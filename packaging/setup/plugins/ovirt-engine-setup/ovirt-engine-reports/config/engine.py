#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2013-2014 Red Hat, Inc.
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
_ = lambda m: gettext.dgettext(message=m, domain='ovirt-engine-reports')


from otopi import constants as otopicons
from otopi import util
from otopi import filetransaction
from otopi import plugin


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.reports import constants as oreportscons


@util.export
class Plugin(plugin.PluginBase):

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
        after=(
            oreportscons.Stages.CORE_ENABLE,
            oreportscons.Stages.ENGINE_CORE_ENABLE,
        ),
    )
    def _customization(self):
        reports_conf_content = (
            'ENGINE_REPORTS_BASE_URL='
                'https://{fqdn}/ovirt-engine-reports\n'
            'ENGINE_REPORTS_DASHBOARD_URL='
                '${{ENGINE_REPORTS_BASE_URL}}'
                '/flow.html?_flowId=viewReportFlow'
                '&viewAsDashboardFrame=true\n'
            'ENGINE_REPORTS_PROXY_URL='
                '${{ENGINE_REPORTS_BASE_URL}}/ovirt/reports-interface\n'
            'ENGINE_REPORTS_VERIFY_HOST=true\n'
            'ENGINE_REPORTS_VERIFY_CHAIN=true\n'
            'ENGINE_REPORTS_READ_TIMEOUT=\n'
        ).format(
            fqdn=self.environment[osetupcons.ConfigEnv.FQDN],
        )

        if self.environment[oreportscons.EngineCoreEnv.ENABLE]:
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=oreportscons.EngineFileLocations.
                        OVIRT_ENGINE_SERVICE_CONFIG_REPORTS,
                    content=reports_conf_content,
                    modifiedList=self.environment[
                        otopicons.CoreEnv.MODIFIED_FILES
                    ],
                )
            )
        else:
            self._remote_engine = self.environment[
                osetupcons.CoreEnv.REMOTE_ENGINE
            ]
            self._remote_engine.configure(
                fqdn=self.environment[
                    oreportscons.EngineConfigEnv.ENGINE_FQDN
                ],
            )
            self._remote_engine.copy_to_engine(
                file_name=oreportscons.EngineFileLocations.
                    OVIRT_ENGINE_SERVICE_CONFIG_REPORTS,
                content=reports_conf_content,
            )

    @plugin.event(
        stage=plugin.Stages.STAGE_CLOSEUP,
        condition=lambda self: (
            self.environment[
                oreportscons.CoreEnv.ENABLE
            ] and
            # If on same host as engine, engine setup restarts it
            not self.environment[
                oreportscons.EngineCoreEnv.ENABLE
            ]
        ),
        before=(
            osetupcons.Stages.DIALOG_TITLES_E_SUMMARY,
        ),
        after=(
            osetupcons.Stages.DIALOG_TITLES_S_SUMMARY,
        ),
    )
    def _closeup(self):
        self._remote_engine.execute_on_engine(
            cmd='service ovirt-engine restart',
            timeout=120,
            text=_(
                'To update the connections to Reports on the engine, '
                'please restart the engine service, '
                'by running the following command on the engine host:\n'
                '# service ovirt-engine restart'
            ),
        )


# vim: expandtab tabstop=4 shiftwidth=4
