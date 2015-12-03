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


"""Export saved reports plugin."""


import gettext
import os

from otopi import plugin, util

from ovirt_engine_setup import dialog
from ovirt_engine_setup.reports import constants as oreportscons
from ovirt_engine_setup.reports import reportsutil as oreportsutil


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """Export saved reports plugin."""

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
                'name': oreportscons.Const.TOOL_ACTION_EXPORT_SAVED_REPORTS,
                'desc': _(
                    'Export Jasperreports saved reports to a zip file'
                ),
            }
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        after=(
            oreportscons.Stages.TOOL_ACTION_SELECTED,
        ),
        condition=lambda (self): self.environment[
            oreportscons.ToolEnv.ACTION
        ] == oreportscons.Const.TOOL_ACTION_EXPORT_SAVED_REPORTS,
    )
    def _customization(self):

        def writable(f):
            res = ''
            try:
                with open(self.resolveFile(f), 'a'):
                    pass
                res = ''
            except IOError:
                res = _('Cannot write to {f}').format(f=f)
            return res

        dialog.queryEnvKey(
            dialog=self.dialog,
            logger=self.logger,
            env=self.environment,
            key=oreportscons.ToolEnv.FILE,
            note=_(
                'Filename to export saved reports to: '
            ),
            prompt=True,
            tests=(
                {
                    'test': lambda(f): _(
                        'File {f} exists'
                    ).format(f=f) if os.path.exists(
                        self.resolveFile(f)
                    ) else '',
                    'is_error': False,
                    'warn_note': 'Overwrite? ',
                },
                {
                    'test': writable,
                },
            ),
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda (self): self.environment[
            oreportscons.ToolEnv.ACTION
        ] == oreportscons.Const.TOOL_ACTION_EXPORT_SAVED_REPORTS,
    )
    def _misc_export(self):
        self._oreportsutil.set_jasper_name()
        f = self.resolveFile(
            self.environment[
                oreportscons.ToolEnv.FILE
            ]
        )
        self.logger.info(_('Exporting saved reports to {f}').format(f=f))
        self._oreportsutil.execute(
            args=(
                './js-export.sh',
                '--uris', (
                    '/organizations/organization_1/adhoc/aru'
                    if (
                        self.environment[
                            oreportscons.JasperEnv.JASPER_NAME
                        ] == 'pro'
                    ) else '/saved_reports'
                ),

                '--output-zip', f,
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4
