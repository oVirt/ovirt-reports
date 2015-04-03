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


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup import hostname as osetuphostname
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
            oreportscons.EngineConfigEnv.ENGINE_FQDN,
            None
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        after=(
            osetupcons.Stages.DIALOG_TITLES_S_NETWORK,
            oengcommcons.Stages.NETWORK_OWNERS_CONFIG_CUSTOMIZED,
        ),
        before=(
            osetupcons.Stages.DIALOG_TITLES_E_NETWORK,
        ),
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
    )
    def _customization(self):
        osetuphostname.Hostname(
            plugin=self,
        ).getHostname(
            envkey=oreportscons.EngineConfigEnv.ENGINE_FQDN,
            whichhost=_('the engine'),
            supply_default=False,
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
    )
    def misc(self):
        uninstall_files = []
        self.environment[
            osetupcons.CoreEnv.REGISTER_UNINSTALL_GROUPS
        ].addFiles(
            group='ovirt_reports_files',
            fileList=uninstall_files,
        )
        self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
            filetransaction.FileTransaction(
                name=oreportscons.FileLocations.SSO_CONFIGURATION,
                content=(
                    'sslInsecure = true\n'
                    'getSessionUserGetSessionUserServletURL = '
                    'https://{host}:{port}/ovirt-engine/services'
                    '/get-session-user\n'
                ).format(
                    host=self.environment[
                        oreportscons.EngineConfigEnv.ENGINE_FQDN
                    ],
                    # TODO - this should be customizable as well, but default
                    # works (443).
                    port=self.environment[
                        oengcommcons.ConfigEnv.PUBLIC_HTTPS_PORT
                    ],
                ),
                modifiedList=uninstall_files,
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4
