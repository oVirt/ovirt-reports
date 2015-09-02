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


"""Import saved reports plugin."""


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
    """Import saved reports plugin."""

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
                'name': oreportscons.Const.TOOL_ACTION_IMPORT_SAVED_REPORTS,
                'desc': _(
                    'Import a saved reports zip file to Jasperreports'
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
        ] == oreportscons.Const.TOOL_ACTION_IMPORT_SAVED_REPORTS,
    )
    def _customization(self):

        def readable(f):
            res = ''
            try:
                with open(f, 'r'):
                    pass
                res = ''
            except IOError:
                res = _('Cannot read from {f}').format(f=f)
            return res

        dialog.queryEnvKey(
            dialog=self.dialog,
            logger=self.logger,
            env=self.environment,
            key=oreportscons.ToolEnv.FILE,
            note=_('Filename to import saved reports from: '),
            prompt=True,
            tests=(
                {
                    'test': lambda(f): (
                        '' if os.path.exists(self.resolveFile(f))
                        else _('File {f} not found'.format(f=f))
                    ),
                },
                {
                    'test': readable,
                },
            ),
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda (self): self.environment[
            oreportscons.ToolEnv.ACTION
        ] == oreportscons.Const.TOOL_ACTION_IMPORT_SAVED_REPORTS,
    )
    def _misc_import(self):
        f = self.resolveFile(
            self.environment[
                oreportscons.ToolEnv.FILE
            ]
        )
        self.logger.info(_('Importing saved reports from {f}').format(f=f))
        self._oreportsutil.execute(
            args=(
                './js-import.sh',
                '--input-zip', f,
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4
