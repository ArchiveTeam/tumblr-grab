#!/usr/bin/env bash

# god, please forgive me for this mess

if [ "${1}" == "test" ]; then
	shift
	uax="${1}"
	shift
	pfg="${1}"
	shift
	echo "${@}"
	html=$(curl -sf https://staff.tumblr.com/ -A "${uax}" -H "Cookie: pfg=${pfg}") || echo "curl fail: ${uax} ${pfg}"
	echo "${html}" | fgrep -q '/181199101690/hey-tumblr-a-couple-of-weeks-ago-we-announced-an"' || echo "grep fail: ${uax} ${pfg}"
	echo "ok: ${uax} ${pfg}"
	exit 0
fi

cat cookies.json | jq -r '.[] | ["./test.sh", "test", .uax, .pfg] | @sh' | bash
