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


"""Database plugin."""


import gettext


from otopi import constants as otopicons
from otopi import filetransaction
from otopi import plugin
from otopi import util


from ovirt_engine import util as outil


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """Databsae plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
    )
    def _misc(self):
        uninstall_files = []
        self.environment[
            osetupcons.CoreEnv.REGISTER_UNINSTALL_GROUPS
        ].addFiles(
            group='ovirt_reports_files',
            fileList=uninstall_files,
        )
        self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
            filetransaction.FileTransaction(
                name=(
                    oreportscons.FileLocations.
                    REPORTS_SERVICE_CONFIG_DATABASE
                ),
                mode=0o600,
                owner=self.environment[osetupcons.SystemEnv.USER_ENGINE],
                enforcePermissions=True,
                content=(
                    'DWH_DB_HOST="{host}"\n'
                    'DWH_DB_PORT="{port}"\n'
                    'DWH_DB_USER="{user}"\n'
                    'DWH_DB_PASSWORD="{password}"\n'
                    'DWH_DB_DATABASE="{db}"\n'
                    'DWH_DB_SECURED="{secured}"\n'
                    'DWH_DB_SECURED_VALIDATION="{securedValidation}"\n'
                ).format(
                    host=self.environment[oreportscons.DWHDBEnv.HOST],
                    port=self.environment[oreportscons.DWHDBEnv.PORT],
                    user=self.environment[oreportscons.DWHDBEnv.USER],
                    password=outil.escape(
                        self.environment[oreportscons.DWHDBEnv.PASSWORD],
                        '"\\$',
                    ),
                    db=self.environment[oreportscons.DWHDBEnv.DATABASE],
                    secured=self.environment[oreportscons.DWHDBEnv.SECURED],
                    securedValidation=self.environment[
                        oreportscons.DWHDBEnv.SECURED_HOST_VALIDATION
                    ],
                ),
                modifiedList=uninstall_files,
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4
