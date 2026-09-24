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

"""Block until the stack under test is up, then let the replay start.

The recorder, test launch, and player all start together. If the stack under test isn't ready, the bag may finish before key topics exist—causing empty output and hard-to-diagnose failures.

We can't just wait for publishers on the expected output topics. Nodes running with sim time won't publish until `/clock` arrives (which only happens after the player starts), creating a potential deadlock. However, these nodes subscribe to `/clock` as soon as they're up, signaling readiness.

This function waits for the first of:
* All expected output topics have publishers (stack uses wall-clock time, already running).
* A `/clock` subscription appears (stack uses sim time, waiting for the player). We then briefly wait for any remaining publishers.
"""

import argparse
import sys
import time

import rclpy
from rclpy.node import Node

from .logging_config import get_logger

_logger_ = get_logger()

CLOCK_TOPIC = '/clock'


def wait_for_stack(
    topics: list[str],
    timeout: float,
    grace: float = 2.0,
    poll_period: float = 0.1,
) -> tuple[bool, list[str]]:
    """Wait until the stack under test is up.

    Returns (saw_clock_subscriber, topics still without a publisher).
    """
    node = Node('replay_testing_wait_for_stack')
    pending = list(topics)
    saw_clock = False

    def poll():
        # The graph view only refreshes while the node is spun, so polling it
        # without spinning never sees anything appear.
        rclpy.spin_once(node, timeout_sec=poll_period)
        return [t for t in pending if not node.get_publishers_info_by_topic(t)]

    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            pending = poll()
            if topics and not pending:
                return False, []
            if node.get_subscriptions_info_by_topic(CLOCK_TOPIC):
                saw_clock = True
                break

        if not saw_clock:
            return False, pending

        # Sim-time nodes are up; give any wall-clock outputs a moment to appear.
        grace_deadline = min(deadline, time.monotonic() + grace)
        while pending and time.monotonic() < grace_deadline:
            pending = poll()
    finally:
        node.destroy_node()

    return saw_clock, pending


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('topics', nargs='*', help='Topics expected to be published')
    parser.add_argument('--timeout', type=float, default=30.0)
    parser.add_argument('--grace', type=float, default=2.0)
    args = parser.parse_args(argv)

    rclpy.init()
    try:
        saw_clock, missing = wait_for_stack(args.topics, args.timeout, args.grace)
    finally:
        if rclpy.ok():
            rclpy.shutdown()

    if not saw_clock and missing:
        # Not fatal: a test may legitimately declare an output it only reaches
        # once the replay is under way, and failing here would hide that behind
        # a launch error instead of the analyze assertion that explains it.
        _logger_.warning(
            f'Starting playback without a ready stack; no publisher on {sorted(missing)} '
            f'and nothing subscribed to {CLOCK_TOPIC}'
        )
    return 0


if __name__ == '__main__':
    sys.exit(main())
