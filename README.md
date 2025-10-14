# Replay Testing

A ROS2-based framework for configuring, authoring and running replay tests.

Features include:
- MCAP replay and automatic recording of assets for offline review
- Baked-in Unittest support for MCAP asserts
- Parametric sweeps
- Easy-to-use CMake for running in CI
- Lightweight CLI for running quickly

## What is Replay Tesing?

Replay testing is simply a way to replay previously recorded data into your own set of ROS nodes. When you are iterating on a piece of code, it is typically much easier to develop it on your local machine rather than on robot. Therefore, if you are able to record that data on-robot first, and then replay locally, you get the best of both worlds!

All robotics developers use replay testing in one form or another. This package just wraps many of the conventions into an easy executable.

## Usage

### CLI

```
ros2 run replay_testing replay_test [REPLAY_TEST_PATH]
```

Run `@analyze` only on a previous run:

```
ros2 run replay_testing replay_test [REPLAY_TEST_PATH] --analyze [RUN_ID]
```

For other args:

```
ros2 run replay_testing replay_test --help
```

### `colcon test` and CMake

This package exposes CMake you can use for running replay tests as part of your own package's testing pipeline.

To use:

```cmake
find_package(replay_testing REQUIRED)

..

if(BUILD_TESTING)
  add_replay_test([REPLAY_TEST_PATH])
endif()

```

If you've set up your CI to persist artifact paths under `test_results`, you should see a `*.xunit.xml` file be produced based on the `REPLAY_TEST_PATH` you provided.

## Authoring Replay Tests

Each replay test can be authored into its own file, like `my_replay_test.py`. We expose a set of Python decorators that you wrap each class for your test.

Replay testing has three distinct phases, **all of which are required to run a replay test**:

### Filter Fixtures `@fixtures`

For collecting and preparing your fixtures to be run against your launch specification. Duties include:
- Provides a mechanism for specifying your input fixtures (e.g. `lidar_data.mcap`). If you want to store your MCAPs outside of source control, see [Storing MCAP](#storing-mcap) below.
- Filtering out any expected output topics that will be produced from the `run` step.
- Produces a `filtered_fixture.mcap` asset that is used against the `run` step
- Asserts that specified input topics are present
- (Eventually) Provides ways to make your old data forwards compatible with updates to your robotics stack

Here is how you use it:

```python
@fixtures.parameterize([LocalFixture(path="/tmp/mcap/my_data.mcap")])
class FilterFixtures:
    required_input_topics = ["/vehicle/cmd_vel"]
    expected_output_topics = ["/user/cmd_vel"]
```

### Run `@run`

Specify a launch description that will run against the replayed fixture. Usage:

```python
@run.default()
class Run:
    def generate_launch_description(self) -> LaunchDescription:
        return LaunchDescription(" YOUR LAUNCH DESCRIPTION ")
```

If you'd like to specify a parameter sweep, you can use the variant:

```python
@run.parameterize(
    [
        ReplayRunParams(name="name_of_your_test", params={..}),
    ]
)
class Run:
    def generate_launch_description(
        self, replay_run_params: ReplayRunParams # Keyed by `name`
    ) -> LaunchDescription:
      return LaunchDescription(" YOUR LAUNCH DESCRIPTION ")
```

Parameterizing your `run` will result in the `analyze` step being run n-param times.

#### QOS Overrides

Depending on use

```python
@run.default()
class Run:
    qos_overrides_yaml = "[PATH_TO_YAML]"
    ...rest of def
```

#### Clock Configuration

By default, replay tests use `/clock` topic for time synchronization. You can disable this behavior using `ReplayRunParams`:

```python
from replay_testing import ReplayRunParams, RunnerArgs

@run.default(params=ReplayRunParams(name='default', params={}, runner_args=RunnerArgs(use_clock=False)))
class Run:
    def generate_launch_description(self) -> LaunchDescription:
        # Your launch description here
        pass
```

When `use_clock=True` (default), the replay framework will:
- Publish `/clock` messages from the MCAP file to synchronize time

When `use_clock=False`, the replay will:
- Skip `/clock` topic publishing

### Analyze `@analyze`

The analyze step is run after the mcap from the `run` is recorded and written. It is a basic wrapper over `unittest.TestCase`, so any `unittest` assertions are built in.

It also wraps an initialized MCAP reader `self.reader` (a `rosbag2_py.SequentialReader`) that you can use to assert against expected message output.

Example:

```python
from replay_testing import read_messages

@analyze
class Analyze:
    def test_cmd_vel(self):
        msgs_it = read_messages(
            self.reader, topics=["/user/cmd_vel"]
        )

        msgs = [(topic_name, msg, timestamp) for topic_name, msg, timestamp in msgs_it]
        assert len(msgs) >= 1
        assert msgs[0][0] == "/user/cmd_vel"
```

### Full Example

```python
from replay_testing import (
    fixtures,
    run,
    analyze,
    LocalFixture,
    read_messages,
)
from launch import LaunchDescription
from launch.actions import ExecuteProcess

import pathlib


@fixtures.parameterize([LocalFixture(path="/tmp/mcap/my_data.mcap")])
class Fixtures:
    input_topics = ["/vehicle/cmd_vel"]
    output_topics = ["/user/cmd_vel"]


@run.default()
class Run:
    def generate_launch_description(self) -> LaunchDescription:
        return LaunchDescription(
            [
                ExecuteProcess(
                    cmd=[
                        "ros2",
                        "topic",
                        "pub",
                        '--use-sim-time',
                        "-r",
                        "10",
                        "/user/cmd_vel",
                        "geometry_msgs/msg/Twist",
                        "{linear: {x: 1.0}, angular: {z: 0.5}}",
                    ],
                    name="topic_pub",
                    output="screen",
                )
            ]
        )


@analyze
class AnalyzeBasicReplay:
    def test_cmd_vel(self):
        msgs_it = read_messages(
            self.reader, topics=["/user/cmd_vel"]
        )

        msgs = [(topic_name, msg, timestamp) for topic_name, msg, timestamp in msgs_it]
        assert len(msgs) >= 1
        assert msgs[0][0] == "/user/cmd_vel"

```

## Reviewing MCAP from Replay Tests

If you'd like to directly view the resulting replay results in tools like Foxglove, `replay_testing` will produce and print the result directory under `/tmp/replay_testing`. Example:

```
/tmp/replay_testing/a00a98aa-7f24-45c6-9299-b6232dcd842d/cmd_vel_only/runs/default
```

The guide here is dynamically generated, and within that directory you can find all of your run results under the `runs` subdirectory.

## Storing MCAP

Most of your bags are going to be well past what's reasonable to track in source control. `replay_testing` is compatible with S3 storage compatiable sources (AWS, Backblaze B2, Wasabi etc), you just have to use the `S3Fixture` helper class in your `@fixtures` step:

```python
@fixtures.parameterize([S3Fixture(key='generic/cmd_vel_only.mcap')])
class Fixtures:
    required_input_topics = ['/vehicle/cmd_vel']
    expected_output_topics = ['/user/cmd_vel']
```

When developing locally, you can use the `--env` argument to point to a local env file with your credentials, or source them in your environment some other way.

The variables you'll need are:

```bash
AWS_ACCESS_KEY_ID=[YOUR_KEY]
AWS_SECRET_ACCESS_KEY=[YOUR_SECRET]
AWS_DEFAULT_REGION=[REGION e.g. us-west-2]
AWS_S3_ENDPOINT_URL=[YOUR_URL]
AWS_BUCKET=[YOUR_BUCKET_NAME]
```

## Developing

### Activating Code Standard Hooks

[Pre-commit](https://pre-commit.com) hooks are provided to maintain code standards for this repository.

1. If you do not have pre-commit installed, run `python3 -m pip install pre-commit`
1. For preexisting repositories, you must run `pre-commit install` in that repository
1. You can automatically install pre-commit for newly cloned repositories by running

    ```
 $ git config --global init.templateDir ~/.git-template
    $ pre-commit init-templatedir ~/.git-template
    pre-commit installed at /home/asottile/.git-template/hooks/pre-commit
    ```

Now all git commits will be automatically gated by the configured checks.

## FAQ

> Why MCAP?

We've built most of our internal tooling around Foxglove, which supports MCAP best. The Foxglove team has published a robust set of libraries for writing and reading MCAP that we've used successfully here.

> Can this package support other forms of recorded data? E.g. *.db3

Certainly open to it!
