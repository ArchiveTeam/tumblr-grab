#!/usr/bin/env sh

if ! sudo pip freeze | grep -q warc==0.2.1
then
  echo "Installing warc"
  if ! sudo pip install warc --upgrade
  then
    exit 1
  fi
fi

if ! sudo pip freeze | grep -q requests
then
  echo "Installing requests"
  if ! sudo pip install requests
  then
    exit 1
  fi
fi

exit 0

