#!/usr/bin/env bash

# god, please forgive me for this mess

if [ "${1}" == "test" ]; then
	shift
	uax="${1}"
	shift
	pfx="${1}"
	shift
	pfg="${1}"
	shift
	echo "${@}"
	html=$(curl -sf https://abrandecarlo.tumblr.com/ -A "${uax}" -H "Cookie: pfx=${pfx}; pfg=${pfg}") || echo "curl fail: ${uax} ${pfx} ${pfg}"
	echo "${html}" | fgrep -q "https://66.media.tumblr.com/789bd80dd17403b2e2e48e5cd7d932db/tumblr_o2yy1opbLu1qkpb5to1_1280.jpg" || echo "grep fail: ${uax} ${pfx} ${pfg}"
	echo "ok: ${uax} ${pfx} ${pfg}"
	exit 0
fi

cat cookies.json | jq -r '.[] | ["./test.sh", "test", .uax, .pfx, .pfg] | @sh' | bash
