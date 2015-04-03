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


"""Java plugin."""


import gettext


from otopi import constants as otopicons
from otopi import filetransaction
from otopi import plugin
from otopi import util


from ovirt_engine import configfile


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """Misc plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ConfigEnv.HEAP_MIN,
            None
        )
        self.environment.setdefault(
            oreportscons.ConfigEnv.HEAP_MAX,
            None
        )
        self._enabled = False

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        after=(
            oreportscons.Stages.CORE_ENABLE,
        ),
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
    )
    def _customization(self):
        config = configfile.ConfigFile([
            oreportscons.FileLocations.SERVICE_VARS,
        ])

        if not (
            config.get('HEAP_MIN') and
            config.get('HEAP_MAX')
        ):
            self._enabled = True

        calculated_heap_size = '{sizemb}M'.format(
            sizemb=max(
                1024,
                self.environment[osetupcons.ConfigEnv.TOTAL_MEMORY_MB] / 4
            )
        )

        if self.environment[
            oreportscons.ConfigEnv.HEAP_MIN
        ] is None:
            self.environment[
                oreportscons.ConfigEnv.HEAP_MIN
            ] = config.get('HEAP_MIN') or calculated_heap_size

        if self.environment[
            oreportscons.ConfigEnv.HEAP_MAX
        ] is None:
            self.environment[
                oreportscons.ConfigEnv.HEAP_MAX
            ] = config.get('HEAP_MAX') or calculated_heap_size

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: self._enabled,
    )
    def _misc(self):
        self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
            filetransaction.FileTransaction(
                name=(
                    oreportscons.FileLocations.REPORTS_SERVICE_CONFIG_JAVA
                ),
                content=[
                    'HEAP_MIN="{heap_min}"'.format(
                        heap_min=self.environment[
                            oreportscons.ConfigEnv.HEAP_MIN
                        ],
                    ),
                    'HEAP_MAX="{heap_max}"'.format(
                        heap_max=self.environment[
                            oreportscons.ConfigEnv.HEAP_MAX
                        ],
                    ),
                ],
                modifiedList=self.environment[
                    otopicons.CoreEnv.MODIFIED_FILES
                ],
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4
