#!/bin/sh
#
# ovirt-engine-reports-tool
# Copyright (C) 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

die() {
	local m="$1"
	echo "FATAL: ${m}" >&2
	exit 1
}

usage() {
	cat << __EOF__
Usage: $0
    --log=file
        write log to this file.
    --config=file
        Load configuration files.
    --config-append=file
        Load extra configuration files or answer file.
    --generate-answer=file
        Generate answer file.
    --export-saved-reports
        Export saved reports.
    --import-saved-reports
        Import saved reports.
    --change-reports-admin-password
        Change Reports admin password.

__EOF__
	exit 1
}

script="$(readlink -f "$0")"
scriptdir="$(dirname "${script}")"
. "${scriptdir}/ovirt-engine-reports-tool.env"
baseenv="\"APPEND:BASE/pluginPath=str:${scriptdir}/../plugins\" APPEND:BASE/pluginGroups=str:ovirt-engine-common:ovirt-engine-reports-tool"
otopienv=""

environment="OVESETUP_CORE/offlinePackager=bool:True"
environment="${environment} PACKAGER/yumpackagerEnabled=bool:False"

while [ -n "$1" ]; do
	x="$1"
	v="${x#*=}"
	shift
	case "${x}" in
		--otopi-environment=*)
			otopienv="${v}"
			;;
		--log=*)
			environment="${environment} \"CORE/logFileName=str:${v}\""
			;;
		--config=*)
			environment="${environment} \"APPEND:CORE/configFileName=str:${v}\""
			;;
		--config-append=*)
			environment="${environment} \"APPEND:CORE/configFileAppend=str:${v}\""
			;;
		--generate-answer=*)
			environment="${environment} \"OVESETUP_CORE/answerFile=str:${v}\""
			;;
		--export-saved-reports)
			environment="${environment} \"OVESETUP_REPORTS_TOOL/action=str:exportSavedReports\""
			;;
		--import-saved-reports)
			environment="${environment} \"OVESETUP_REPORTS_TOOL/action=str:importSavedReports\""
			;;
		--change-reports-admin-password)
			environment="${environment} \"OVESETUP_REPORTS_TOOL/action=str:changeAdminPassword\""
			;;
		--help)
			usage
			;;
		*)
			die "Invalid option '${x}'"
			;;
	esac
done

exec "${otopidir}/otopi" "${baseenv} ${environment} ${otopienv}"
