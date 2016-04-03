#
# ovirt-engine-setup -- ovirt engine setup
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


"""Misc plugin."""


import gettext

from otopi import constants as otopicons
from otopi import plugin, util

from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.engine_common import constants as oengcommcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """Misc plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_BOOT,
        before=(
            otopicons.Stages.CORE_LOG_INIT,
        ),
        priority=plugin.Stages.PRIORITY_HIGH - 10,
    )
    def _preinit(self):
        self.environment.setdefault(
            otopicons.CoreEnv.LOG_DIR,
            oreportscons.FileLocations.OVIRT_REPORTS_TOOL_LOG_DIR
        )
        self.environment.setdefault(
            otopicons.CoreEnv.LOG_FILE_NAME_PREFIX,
            oreportscons.FileLocations.OVIRT_REPORTS_TOOL_LOG_PREFIX
        )
        self.environment[
            osetupcons.CoreEnv.ACTION
        ] = oreportscons.Const.ACTION_REPORTS_TOOL

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ToolEnv.FILE,
            None
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_SETUP,
    )
    def _setup(self):
        self.environment[osetupcons.CoreEnv.GENERATE_POSTINSTALL] = False
        self.environment[osetupcons.SystemEnv.HOSTILE_SERVICES] = ''
        self.environment[
            oengcommcons.ConfigEnv.ENGINE_SERVICE_STOP_NEEDED
        ] = False


# vim: expandtab tabstop=4 shiftwidth=4
