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

"""Declare topics that need to be rebuilt during replay.

Some topics can't be directly replayed from a bag due to missing data, mismatched types, or differing rates. If the bag contains the underlying inputs, and the transformation node is deterministic, these can be reconstructed offline.
This helper lets tests specify such regenerate-required topics in one place, avoiding manual keeping of three separate lists: recorded inputs needed for rebuild, outputs to strip from the bag, and launch flags to start the rebuilding nodes. Each is derived from a single, annotated declaration.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegeneratedSource:
    """An input that must be rebuilt during replay instead of replayed.

    ``topic`` is what the replayed node subscribes to, ``recorded_topics`` what the
    bag must carry so it can be rebuilt, and ``launch_argument`` the flag on the
    replay launch that starts the nodes rebuilding it. A rebuild can need more
    than one recorded input, so this takes a tuple rather than a single topic.
    """

    topic: str
    recorded_topics: tuple[str, ...]
    launch_argument: str
    reason: str
    strip_from_replay: bool = True


class ReplaySourcePlan:
    """Work out what a bag must carry, and what has to be rebuilt.

    Given the topics the replayed nodes subscribe to, this splits them into
    topics the bag can replay directly and topics that have to be regenerated
    from something else the bag does carry.
    """

    def __init__(
        self,
        source_topics,
        regenerated: tuple[RegeneratedSource, ...] = (),
    ):
        self.source_topics = set(source_topics)
        self._catalogue = {source.topic: source for source in regenerated}

    @property
    def regenerated(self) -> list[RegeneratedSource]:
        """The sources among the requested ones that must be rebuilt."""
        return [source for topic, source in self._catalogue.items() if topic in self.source_topics]

    @property
    def required_topics(self) -> list[str]:
        """Topics the bag must carry to answer the question.

        Regenerated sources are swapped for the recorded input they are built
        from, since the bag is not expected to carry the derived topic.
        """
        topics = set(self.source_topics)
        for source in self.regenerated:
            topics.discard(source.topic)
            topics.update(source.recorded_topics)
        return sorted(topics)

    @property
    def topics_to_strip(self) -> list[str]:
        """Regenerated topics that must not be replayed from the bag.

        A topic that is both replayed and rebuilt would reach the node twice,
        mixing the recorded rate with the regenerated one. Stripping a topic the
        bag does not carry is a no-op, so every regenerated source is listed.
        """
        return sorted(source.topic for source in self.regenerated if source.strip_from_replay)

    @property
    def launch_arguments(self) -> dict[str, str]:
        """Replay launch flags, one per regeneration, as launch string bools."""
        enabled = {source.launch_argument for source in self.regenerated}
        return {source.launch_argument: str(source.launch_argument in enabled) for source in self._catalogue.values()}

    def describe(self) -> list[str]:
        """One human readable line per regeneration, for the run log."""
        return [
            f'{source.topic}: {source.reason}; rebuilt from {", ".join(source.recorded_topics)}'
            for source in self.regenerated
        ]
