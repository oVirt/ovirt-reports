#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2013-2015 Red Hat, Inc.
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


import gettext


from otopi import constants as otopicons
from otopi import filetransaction
from otopi import plugin
from otopi import util


from ovirt_engine import util as outil


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.engine_common \
    import constants as oengcommcons


from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ApacheEnv.HTTPD_CONF_OVIRT_ENGINE_REPORTS,
            oreportscons.FileLocations.HTTPD_CONF_OVIRT_ENGINE_REPORTS
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: (
            self.environment[oreportscons.CoreEnv.ENABLE] and
            not self.environment[
                osetupcons.CoreEnv.DEVELOPER_MODE
            ]
        ),
    )
    def misc(self):
        uninstall_files = []
        self.environment[
            osetupcons.CoreEnv.REGISTER_UNINSTALL_GROUPS
        ].addFiles(
            group='ovirt_reports_files',
            fileList=uninstall_files,
        )
        self.environment[oengcommcons.ApacheEnv.NEED_RESTART] = True
        self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
            filetransaction.FileTransaction(
                name=self.environment[
                    oreportscons.ApacheEnv.HTTPD_CONF_OVIRT_ENGINE_REPORTS
                ],
                content=outil.processTemplate(
                    template=(
                        oreportscons.FileLocations.
                        HTTPD_CONF_OVIRT_ENGINE_REPORTS_TEMPLATE
                    ),
                    subst={
                        '@JBOSS_AJP_PORT@': self.environment[
                            oreportscons.ConfigEnv.JBOSS_AJP_PORT
                        ],
                    },
                ),
                modifiedList=uninstall_files,
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4
