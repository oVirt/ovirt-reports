#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2014-2015 Red Hat, Inc.
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


"""Jboss plugin."""


import gettext
import os


from otopi import constants as otopicons
from otopi import filetransaction
from otopi import plugin
from otopi import util


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """JBoss plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ConfigEnv.OVIRT_REPORTS_JBOSS_HOME,
            oreportscons.FileLocations.OVIRT_REPORTS_DEFAULT_JBOSS_HOME
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
    )
    def _misc(self):
        """
        Check JBOSS_HOME after ovirt-engine upgrade since jboss may be
        upgraded as well and JBOSS_HOME may become invalid.
        This can't be done at package stage since yum transaction is committed
        as last action in that stage.
        """
        if not os.path.exists(
            self.environment[
                oreportscons.ConfigEnv.OVIRT_REPORTS_JBOSS_HOME
            ]
        ):
            raise RuntimeError(
                _('Cannot find Jboss at {jbossHome}').format(
                    jbossHome=self.environment[
                        oreportscons.ConfigEnv.OVIRT_REPORTS_JBOSS_HOME
                    ],
                )
            )

        for f in (
            (
                oreportscons.FileLocations.
                REPORTS_SERVICE_CONFIG_JBOSS
            ),
        ):
            content = [
                'OVIRT_REPORTS_JBOSS_HOME="{jbossHome}"'.format(
                    jbossHome=self.environment[
                        oreportscons.ConfigEnv.OVIRT_REPORTS_JBOSS_HOME
                    ],
                ),
            ]
            if self.environment[osetupcons.CoreEnv.DEVELOPER_MODE]:
                content.append(
                    'REPORTS_LOG_TO_CONSOLE=true'
                )
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=f,
                    content=content,
                    modifiedList=self.environment[
                        otopicons.CoreEnv.MODIFIED_FILES
                    ],
                )
            )


# vim: expandtab tabstop=4 shiftwidth=4
