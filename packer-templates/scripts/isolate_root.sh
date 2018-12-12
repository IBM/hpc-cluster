#! /bin/bash

usage()
{
    echo "Usage: ./isolate_root.sh -i <image-path> [option(s)]

    Program to strip out the root filesystem from a whole machine image.
    Takes in parameters or reads from environment variables

    Options:
        -i, --image             PATH to whole machine image (created from packer)
                                Overrides IMAGE_PATH environment variable
                                Required
        -r, --root-image-name   Name of desired root filesystem (will be suffixed with .img extension)
                                Overrides ROOT_IMAGE_NAME environment variable
                                Default: image
        -p, --partition         Number of partition in whole machine image that contains the root filesystem
                                Overrides PARTITION_NUMBER environment variable
                                Default: 2
"
}

# error_check (last_exit code, error_msg)
# param $1              - exit code of last command executed (contained in $?)
# param $2              - error message to echo
# Sets the IS_ERROR variable to 1 and gracefully exits on error
error_check () {
    # Check if error code is 1
    if [[ "$1" -ne "0" ]]; then
        echo >&2 "$2"
        IS_ERROR="$1"
        # Get absolute path of file
        FULL_FILE_PATH=$(readlink -f -- $0)
        ROOT_CLI_CMD="${FULL_FILE_PATH} -i ${IMAGE_PATH} -r ${ROOT_IMAGE_NAME} -p ${PARTITION_NUMBER}"
        echo ""
        echo "Root isolation unsuccessful. Command to re-run on your own:"
        echo $ROOT_CLI_CMD
        echo ""
        exit 0
    fi
}

# List of functions to clean up
CLEANUP_FUNC_LIST=()
# Executes all clean up functions in CLEANUP_FUNC_LIST
cleanup_func() {
    echo "cleaning up"
    length=${#CLEANUP_FUNC_LIST[*]}
    for (( i=length-1; i >= 0; i-- ))
        do
        # pass exit code since some cleanup functions only run on errors
        ${CLEANUP_FUNC_LIST[i]} $IS_ERROR
    done
}

# Setup default arguments
if [ -z "${ROOT_IMAGE_NAME}" ]; then
    ROOT_IMAGE_NAME="image"
fi

if [ -z "${PARTITION_NUMBER}" ]; then
    PARTITION_NUMBER="2"
fi

# Read in arguments
POSITIONAL=() # For
while [[ $# -gt 0 ]]
    do
    key="$1"

    case $key in
        -i|--image-name)
        IMAGE_PATH="$2"
        shift # past argument
        shift # past value
        ;;
        -r|--root-image-name)
        ROOT_IMAGE_NAME="$2"
        shift # past argument
        shift # past value
        ;;
        -p|--partition)
        PARTITION_NUMBER="$2"
        shift # past argument
        shift # past value
        ;;
        -h|--help)
        usage
        exit
        ;;
        *) # unknown option
        POSITIONAL+=("$1")
        shift
        ;;
    esac
done

KEY_NAME="${ROOT_IMAGE_NAME}.dek"

# Check if image name was given
if [ -z "${IMAGE_PATH}" ]; then
    echo "PATH OF FULL IMAGE_FILE IS REQUIRED"
    exit
fi

if ! [ -x "$(command -v cryptsetup)" ]; then
  echo "Error: cryptsetup executable not found"
  exit
fi

# Run clean up functions on exit
trap cleanup_func EXIT

# Starting with a raw kvm image file
# map image to loopback device
LOOPBACK_DEVICE=$(losetup --show -f "${IMAGE_PATH}")
error_check "$?" "could not setup loopback device"

# Cleanup function for loopback_device
# TODO: /dev/loop* still remains after losetup
unloop () {
    losetup -d "${LOOPBACK_DEVICE}"
}
CLEANUP_FUNC_LIST+=(unloop)

# Seperate partitions created in raw kvm image
kpartx -a -s "${LOOPBACK_DEVICE}"
error_check "$?" "did not set up partitions"

# Clean up partitions
unmappart () {
    kpartx -d "${LOOPBACK_DEVICE}"
}
CLEANUP_FUNC_LIST+=(unmappart)

# Extract the root filesystem to its own archive
# copy (dd) the contents of the filesystem in the specified partition (supposed to be root partition) to a separate file
ROOTFS=/dev/mapper/${LOOPBACK_DEVICE#/dev/}p"${PARTITION_NUMBER}"
dd if=/dev/mapper/${LOOPBACK_DEVICE#/dev/}p"${PARTITION_NUMBER}" of="${ROOT_IMAGE_NAME}"
error_check "$?" "did not extract root filesystem to its own archive"

# Removes root partition image
# Only runs on error exit codes
remove_root_archive () {
    rm "${ROOT_IMAGE_NAME}"
}
CLEANUP_FUNC_LIST+=(remove_root_archive)

# Encrypt the archived filesystem:

# Create a 4KB encryption key:
dd if=/dev/urandom bs=1024 count=4 of="${KEY_NAME}"
error_check "$?" "did not create encryption key"

# Remove the created random key
# Only runs on error exit codes
remove_key () {
    if [[ "$1" -ne "0" ]]; then
        rm "${KEY_NAME}"
    fi
}
CLEANUP_FUNC_LIST+=(remove_key)

# Calculate the size of the encrypted volume (original image size + 4MB header)
orig=$(stat -c %s "${ROOT_IMAGE_NAME}")
new=$(($orig+4194304))
newmb=$(( ($new+1048576-1) / 1048576 ))

# Create raw file with correct number of bytes
dd if=/dev/zero of="${ROOT_IMAGE_NAME}".img bs=1M count=$newmb
error_check "$?" "did not create raw file"

# Remove the encrypted root image
# Only runs on error exit codes
remove_encrypted_root_archive () {
    if [[ "$1" -ne "0" ]]; then
        rm "${ROOT_IMAGE_NAME}".img
    fi
}
CLEANUP_FUNC_LIST+=(remove_encrypted_root_archive)

# Format raw image using dmcrypt
cryptsetup -v -q luksFormat "${ROOT_IMAGE_NAME}".img "${KEY_NAME}"
error_check "$?" "did not format raw image"

# Attach the empty encrypted RAW image as a volume
cryptsetup -v luksOpen "${ROOT_IMAGE_NAME}".img encryptedVolume --key-file "${KEY_NAME}"
error_check "$?" "did not attach empty encrypted RAW image as a volume"

# Close the volume
uncrypt () {
    cryptsetup luksClose encryptedVolume
}
CLEANUP_FUNC_LIST+=(uncrypt)

# Copy The Unencrypted Image Into the encrypted device
dd if="${ROOT_IMAGE_NAME}" of=/dev/mapper/encryptedVolume
error_check "$?" "did not copy unencrypted image into encrypted device"
