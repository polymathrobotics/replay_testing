# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Permission is hereby granted to use, copy, modify, and distribute this software
# in source or binary form, provided that the above copyright notice and this
# permission notice appear in all copies or substantial portions of the software.
#
# This software is provided "as is", without warranty of any kind.
find_package(ament_cmake_test REQUIRED)
find_package(python_cmake_module REQUIRED)
find_package(PythonExtra REQUIRED)

include("${replay_testing_DIR}/add_replay_test.cmake")
