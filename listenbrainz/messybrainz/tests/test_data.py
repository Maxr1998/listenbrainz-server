# messybrainz-server - Server for the MessyBrainz project
#
# Copyright (C) 2017 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA)

from listenbrainz import messybrainz
from listenbrainz.db import timescale
from listenbrainz.db.testing import TimescaleTestCase


recording = {
    'artist': 'Frank Ocean',
    'release': 'Blond',
    'title': 'Pretty Sweet',
    'additional_info': {
        'key1': 'Value1',
    },
    'recording_mbid': "5465ca86-3881-4349-81b2-6efbd3a59451"
}

recording_diff_case = {
    'artist': 'FRANK OCEAN',
    'release': 'BLoNd',
    'title': 'PReTtY SWEET',
    'additional_info': {
        'key1': 'VaLue1',
    },
    'recording_mbid': "5465ca86-3881-4349-81b2-6efbd3a59451"
}


class DataTestCase(TimescaleTestCase):

    def test_submit_recording(self):
        with timescale.engine.connect() as connection:
            recording_msid = messybrainz.submit_recording(connection, recording)
            self.assertEqual(recording_msid, str(messybrainz.get_id_from_recording(connection, recording)))

    def test_add_recording_different_cases(self):
        """ Tests that recordings with only case differences get the same MessyBrainz ID.
        """
        with timescale.engine.connect() as connection:
            msid1 = messybrainz.submit_recording(connection, recording)
            msid2 = str(messybrainz.get_id_from_recording(connection, recording_diff_case))
            self.assertEqual(msid1, msid2)

    def test_load_recordings_from_msids(self):
        with timescale.engine.connect() as connection:
            recording_msid = messybrainz.submit_recording(connection, recording)
            result = messybrainz.load_recordings_from_msids(connection, [recording_msid])[0]
            self.assertDictEqual(result['payload'], recording)

