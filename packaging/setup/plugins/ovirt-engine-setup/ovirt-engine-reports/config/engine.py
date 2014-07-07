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


import os
import gettext
_ = lambda m: gettext.dgettext(message=m, domain='ovirt-engine-reports')


from otopi import constants as otopicons
from otopi import util
from otopi import filetransaction
from otopi import plugin


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.engine_common import database
from ovirt_engine_setup.reports import constants as oreportscons
from ovirt_engine_setup.engine_common \
    import constants as oengcommcons


@util.export
class Plugin(plugin.PluginBase):

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
        after=(
            oengcommcons.Stages.DB_CONNECTION_AVAILABLE,
            oreportscons.Stages.JASPER_NAME_SET,
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
        with open(
            oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_UI,
            "r",
        ) as content:
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=os.path.join(
                        oreportscons.FileLocations.OVIRT_ENGINE_LOCALSTATEDIR,
                        'reports.xml',
                    ),
                    content=content.read(),
                    modifiedList=uninstall_files,
                )
            )

        statement = database.Statement(
            dbenvkeys=oreportscons.Const.ENGINE_DB_ENV_KEYS,
            environment=self.environment,
        )

        result = statement.execute(
            statement="""
                update vdc_options
                set
                    option_value=%(value)s
                where
                    option_name=%(name)s and
                    version=%(version)s
            """,
            args=dict(
                name='RedirectServletReportsPage',
                value='https://{fqdn}:{port}/ovirt-engine-reports'.format(
                    fqdn=self.environment[osetupcons.ConfigEnv.FQDN],
                    port=self.environment[
                        oreportscons.ConfigEnv.PUBLIC_HTTPS_PORT
                    ],
                ),
                version='general',
            ),
            ownConnection=False,
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
        self.dialog.note(
            text=_(
                'To update the Reports link on the main web interface page, '
                'please restart the engine service, '
                'by running the following command on the engine host:\n'
                '# service ovirt-engine restart'
            ),
        )


# vim: expandtab tabstop=4 shiftwidth=4
