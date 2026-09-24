# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Unit tests for declaring topics that must be rebuilt during a replay."""

import pytest

from replay_testing import RegeneratedSource, ReplaySourcePlan

# A stand-in for a topic the bag does not carry, rebuilt from one that it does.
DERIVED = RegeneratedSource(
    topic='/filtered_cloud',
    recorded_topics=('/raw_cloud',),
    launch_argument='regenerate_filtered_cloud',
    reason='not recorded; only the raw cloud is',
)

# A stand-in for one that needs several recorded inputs and whose recorded copy
# must survive the replay, because it is the reference the rebuild is judged on.
REBUILT = RegeneratedSource(
    topic='/derived_map',
    recorded_topics=('/image', '/depth'),
    launch_argument='regenerate_derived_map',
    reason='recorded too slowly to drive the node',
    strip_from_replay=False,
)

CATALOGUE = (DERIVED, REBUILT)


class TestDirectlyReplayable:
    def test_plain_topics_are_required_as_they_are(self):
        plan = ReplaySourcePlan(['/scan', '/odom'], regenerated=CATALOGUE)

        assert plan.required_topics == ['/odom', '/scan']
        assert plan.regenerated == []
        assert plan.topics_to_strip == []

    def test_every_known_flag_is_reported_off(self):
        # The launch declares them all, so all of them must be passed rather
        # than left to defaults that could drift.
        plan = ReplaySourcePlan(['/scan'], regenerated=CATALOGUE)

        assert plan.launch_arguments == {
            'regenerate_filtered_cloud': 'False',
            'regenerate_derived_map': 'False',
        }

    def test_nothing_to_describe(self):
        assert ReplaySourcePlan(['/scan'], regenerated=CATALOGUE).describe() == []

    def test_an_empty_catalogue_leaves_everything_alone(self):
        plan = ReplaySourcePlan(['/filtered_cloud'])

        assert plan.required_topics == ['/filtered_cloud']
        assert plan.launch_arguments == {}


class TestRebuiltFromOneInput:
    def test_the_recorded_input_is_required_instead(self):
        plan = ReplaySourcePlan(['/filtered_cloud', '/scan'], regenerated=CATALOGUE)

        assert plan.required_topics == ['/raw_cloud', '/scan']

    def test_the_derived_topic_is_stripped_from_the_replay(self):
        # Replaying it as well would let the recorded copy shadow the rebuilt one.
        plan = ReplaySourcePlan(['/filtered_cloud'], regenerated=CATALOGUE)

        assert plan.topics_to_strip == ['/filtered_cloud']

    def test_only_its_own_flag_turns_on(self):
        plan = ReplaySourcePlan(['/filtered_cloud'], regenerated=CATALOGUE)

        assert plan.launch_arguments['regenerate_filtered_cloud'] == 'True'
        assert plan.launch_arguments['regenerate_derived_map'] == 'False'

    def test_describe_names_both_ends(self):
        (line,) = ReplaySourcePlan(['/filtered_cloud'], regenerated=CATALOGUE).describe()

        assert '/filtered_cloud' in line
        assert '/raw_cloud' in line
        assert 'not recorded' in line


class TestRebuiltFromSeveralInputs:
    def test_all_recorded_inputs_are_required(self):
        plan = ReplaySourcePlan(['/derived_map'], regenerated=CATALOGUE)

        assert plan.required_topics == ['/depth', '/image']

    def test_a_reference_copy_is_kept_in_the_replay(self):
        # strip_from_replay=False: the recorded copy is what the rebuild is
        # measured against, so it has to survive.
        plan = ReplaySourcePlan(['/derived_map'], regenerated=CATALOGUE)

        assert plan.topics_to_strip == []


class TestCombined:
    def test_both_rebuilds_coexist(self):
        plan = ReplaySourcePlan(['/filtered_cloud', '/derived_map', '/scan'], regenerated=CATALOGUE)

        assert plan.required_topics == ['/depth', '/image', '/raw_cloud', '/scan']
        assert plan.topics_to_strip == ['/filtered_cloud']
        assert plan.launch_arguments == {
            'regenerate_filtered_cloud': 'True',
            'regenerate_derived_map': 'True',
        }
        assert len(plan.describe()) == 2

    def test_duplicate_requests_collapse(self):
        plan = ReplaySourcePlan(
            ['/scan', '/scan', '/filtered_cloud', '/filtered_cloud'],
            regenerated=CATALOGUE,
        )

        assert plan.required_topics == ['/raw_cloud', '/scan']
        assert len(plan.regenerated) == 1


@pytest.mark.parametrize('strip', [True, False])
def test_strip_flag_is_carried_through(strip):
    source = RegeneratedSource(
        topic='/x',
        recorded_topics=('/y',),
        launch_argument='f',
        reason='r',
        strip_from_replay=strip,
    )
    plan = ReplaySourcePlan(['/x'], regenerated=(source,))

    assert plan.topics_to_strip == (['/x'] if strip else [])
