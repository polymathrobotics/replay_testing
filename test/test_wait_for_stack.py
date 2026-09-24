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

import time

import pytest
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rosgraph_msgs.msg import Clock

from replay_testing.wait_for_stack import CLOCK_TOPIC, wait_for_stack


@pytest.fixture
def ros():
    rclpy.init()
    yield
    if rclpy.ok():
        rclpy.shutdown()


@pytest.fixture
def helper(ros):
    """A node standing in for the stack under test."""
    node = Node('wait_for_stack_helper')
    yield node
    node.destroy_node()


def test_returns_when_outputs_are_published(helper):
    """A stack on wall-clock time is ready as soon as its outputs exist."""
    helper.create_publisher(Twist, '/stack_output', 1)

    start = time.monotonic()
    saw_clock, pending = wait_for_stack(['/stack_output'], timeout=10.0)

    assert pending == []
    assert saw_clock is False
    assert time.monotonic() - start < 10.0


def test_returns_when_a_node_subscribes_to_the_clock(helper):
    """A stack on sim time is ready once it is waiting for the player.

    Its outputs cannot appear first: nothing publishes until `/clock` does,
    and `/clock` only arrives with the player this wait is gating.
    """
    helper.create_subscription(Clock, CLOCK_TOPIC, lambda _: None, 1)

    start = time.monotonic()
    saw_clock, pending = wait_for_stack(['/never_published'], timeout=10.0, grace=0.5)
    elapsed = time.monotonic() - start

    assert saw_clock is True
    assert pending == ['/never_published']
    # The clock subscriber releases the wait; only the grace period is spent
    # on the output that will never appear before playback.
    assert elapsed < 10.0


def test_times_out_when_nothing_comes_up(ros):
    """Neither signal: report the missing outputs instead of hanging."""
    start = time.monotonic()
    saw_clock, pending = wait_for_stack(['/absent'], timeout=1.0)

    assert saw_clock is False
    assert pending == ['/absent']
    assert time.monotonic() - start >= 1.0


def test_waits_for_the_clock_when_no_outputs_are_declared(helper):
    """With nothing declared, the clock subscription is the only signal."""
    helper.create_subscription(Clock, CLOCK_TOPIC, lambda _: None, 1)

    saw_clock, pending = wait_for_stack([], timeout=10.0, grace=0.1)

    assert saw_clock is True
    assert pending == []
