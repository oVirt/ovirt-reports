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


"""Change Admin Password plugin."""


import gettext
import os

from otopi import plugin, util

from ovirt_engine_setup import dialog
from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.reports import constants as oreportscons
from ovirt_engine_setup.reports import reportsutil as oreportsutil


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """Change Admin Password plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)
        self._oreportsutil = None

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self._oreportsutil = oreportsutil.JasperUtil(plugin=self)

    @plugin.event(
        stage=plugin.Stages.STAGE_SETUP,
    )
    def _setup(self):
        self.environment[
            oreportscons.ToolEnv.AVAILABLE_ACTIONS
        ].append(
            {
                'name': (
                    oreportscons.Const.TOOL_ACTION_CHANGE_ADMIN_PASSWORD
                ),
                'desc': _(
                    'Change the password of the internal Reports Admin',
                ),
            },
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        after=(
            oreportscons.Stages.TOOL_ACTION_SELECTED,
        ),
        condition=lambda (self): self.environment[
            oreportscons.ToolEnv.ACTION
        ] == oreportscons.Const.TOOL_ACTION_CHANGE_ADMIN_PASSWORD,
    )
    def _customization(self):
        dialog.queryPassword(
            dialog=self.dialog,
            logger=self.logger,
            env=self.environment,
            key=oreportscons.ConfigEnv.ADMIN_PASSWORD,
            note=_(
                'Reports admin password: '
            ),
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda (self): self.environment[
            oreportscons.ToolEnv.ACTION
        ] == oreportscons.Const.TOOL_ACTION_CHANGE_ADMIN_PASSWORD,
    )
    def _misc_reports_admin_password(self):
        self.logger.info(_('Exporting users from JasperReports-Server'))
        users = self._oreportsutil.jsexport(
            what='users',
            args=(
                '--users',
            ),
        )

        self.dialog.note(_('Changing Admin password in:'))
        found = False
        for relative in (
            # CE
            os.path.join(
                'users',
                'admin.xml'
            ),
            # PRO
            os.path.join(
                'users',
                'superuser.xml'
            ),
            os.path.join(
                'users',
                'organization_1',
                'admin.xml'
            )
        ):
            absolute = os.path.join(users, relative)
            if os.path.exists(absolute):
                found = True
                self.dialog.note(_('- {relative}').format(relative=relative))
                with oreportsutil.XMLDoc(absolute) as xml:
                    xml.setNodesContent(
                        '/user/password',
                        self.environment[
                            oreportscons.ConfigEnv.ADMIN_PASSWORD
                        ]
                    )
        if not found:
            raise RuntimeError(_('Admin user not found in export'))

        self.logger.info(_('Importing users to Jasperreports'))
        self._oreportsutil.jsimport(users)

    @plugin.event(
        stage=plugin.Stages.STAGE_CLOSEUP,
        before=(
            osetupcons.Stages.DIALOG_TITLES_E_SUMMARY,
        ),
        after=(
            osetupcons.Stages.DIALOG_TITLES_S_SUMMARY,
        ),
        condition=lambda (self): self.environment[
            oreportscons.ToolEnv.ACTION
        ] == oreportscons.Const.TOOL_ACTION_CHANGE_ADMIN_PASSWORD,
    )
    def _closeup(self):
        self.dialog.note(
            _(
                'Reports admin password was changed. Please restart the '
                'Reports service, using the following command, to make the '
                'change effective:\n'
                '# {cmd}\n'
            ).format(
                cmd='service {service} restart'.format(
                    service=oreportscons.Const.SERVICE_NAME,
                ),
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4
