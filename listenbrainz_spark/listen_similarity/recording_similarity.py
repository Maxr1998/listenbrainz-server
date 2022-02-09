import logging
from datetime import datetime

import pyspark.sql

import listenbrainz_spark
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.schema import recording_similarity_index_schema
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_new_dump

logger = logging.getLogger(__name__)


def calculate(window_size: int, similarity_threshold: float, time_threshold: int):
    decrement = 1.0 / window_size

    from_date, to_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1), datetime.now()
    listens_df = get_listens_from_new_dump(from_date, to_date)
    table = "rec_sim_listens"
    listens_df.createOrReplaceTempView(table)

    scattered_df: pyspark.sql.DataFrame = listenbrainz_spark.session.createDataFrame([], recording_similarity_index_schema)

    weight = 1.0
    for idx in range(1, window_size + 1):
        query = f"""
            WITH mbid_similarity AS (
                SELECT recording_mbid AS mbid0
                     , LEAD(recording_mbid, {idx}) OVER row_next AS mbid1
                     ,    ( recording_mbid != LEAD(recording_mbid, {idx}) OVER row_next
                        -- spark-sql supports interval types but pyspark doesn't so currently need to convert to bigints
                        AND BIGINT(LEAD(listened_at, {idx}) OVER row_next) - BIGINT(listened_at) <= {time_threshold}
                       ) AS similar
                  FROM {table}
                 WHERE recording_mbid IS NOT NULL 
                WINDOW row_next AS (PARTITION BY user_id ORDER BY listened_at)
            ), symmetric_index AS (
                SELECT CASE WHEN mbid0 < mbid1 THEN mbid0 ELSE mbid1 END AS lexical_mbid0
                     , CASE WHEN mbid0 > mbid1 THEN mbid0 ELSE mbid1 END AS lexical_mbid1
                  FROM mbid_similarity
                 WHERE mbid0 IS NOT NULL
                   AND mbid1 IS NOT NULL
                   AND similar
            )
            SELECT lexical_mbid0 AS mbid0
                 , lexical_mbid1 AS mbid1
                 , COUNT(*) * {weight} AS similarity
              FROM symmetric_index
          GROUP BY lexical_mbid0, lexical_mbid1
        """
        scattered_df = scattered_df.union(run_query(query))
        weight -= decrement
        logger.info("Count after iteration %d: %d", idx, scattered_df.count())

    rec_sim_table = "recording_similarity_index_scattered"
    scattered_df.createOrReplaceTempView(rec_sim_table)
    rec_sim_query = f"""
        SELECT mbid0
             , mbid1
             , SUM(similarity) AS total_similarity
          FROM {rec_sim_table}
      GROUP BY mbid0, mbid1
        HAVING total_similarity > {similarity_threshold}
    """
    rec_sim_index_df = run_query(rec_sim_query)
    logger.info("Index Count: %d", rec_sim_index_df.count())
    rec_sim_index_df.write.csv(f"/recording_similarity_index/{window_size}/", mode="overwrite")