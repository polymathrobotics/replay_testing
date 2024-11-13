# Set the target path for the mcap binary
set(MCAP_BINARY_PATH "/usr/local/bin/mcap")

# Define a function to install the mcap binary if it doesn't exist
function(install_mcap)
    message(STATUS "Checking for mcap binary at ${MCAP_BINARY_PATH}...")
    
    if(NOT EXISTS ${MCAP_BINARY_PATH})
        message(STATUS "Downloading mcap binary...")
        execute_process(
            COMMAND curl -L -o ${MCAP_BINARY_PATH} https://github.com/foxglove/mcap/releases/download/releases%2Fmcap-cli%2Fv0.0.47/mcap-linux-amd64
            RESULT_VARIABLE DOWNLOAD_RESULT
        )

        if(NOT ${DOWNLOAD_RESULT} EQUAL 0)
            message(FATAL_ERROR "Failed to download the mcap binary.")
        endif()

        execute_process(
            COMMAND chmod +x ${MCAP_BINARY_PATH}
            RESULT_VARIABLE CHMOD_RESULT
        )

        if(NOT ${CHMOD_RESULT} EQUAL 0)
            message(FATAL_ERROR "Failed to set executable permissions on the mcap binary.")
        endif()

        message(STATUS "mcap binary installed successfully.")
    else()
        message(STATUS "mcap binary already exists, skipping download.")
    endif()
endfunction()
