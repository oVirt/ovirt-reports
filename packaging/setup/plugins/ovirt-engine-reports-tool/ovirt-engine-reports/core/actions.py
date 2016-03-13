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


"""Actions plugin."""


import gettext

from otopi import plugin
from otopi import util

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
            oreportscons.ToolEnv.AVAILABLE_ACTIONS,
            []
        )
        self.environment.setdefault(
            oreportscons.ToolEnv.ACTION,
            None
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        name=oreportscons.Stages.TOOL_ACTION_SELECTED,
        condition=lambda (self): self.environment[
            oreportscons.ToolEnv.ACTION
        ] is None,
    )
    def _customization(self):
        actions = [
            (_(str(i)), action)
            for i, action in enumerate(
                sorted(
                    self.environment[
                        oreportscons.ToolEnv.AVAILABLE_ACTIONS
                    ],
                    key=lambda (action): action['name']
                ),
                start=1
            )
        ]
        self.logger.debug('actions: %s', actions)
        res = self.dialog.queryString(
            name='OVESETUP_REPORTS_TOOL_ACTION',
            note=_(
                '\nPlease choose the action you would like this tool to take:'
                '\n\n{actions}\n'
                '(@VALUES@) []: '
            ).format(
                actions='\n'.join(
                    '({i}) {desc}\n'.format(
                        i=item[0],
                        desc=item[1]['desc'],
                    )
                    for item in actions
                ),
            ),
            prompt=True,
            validValues=[item[0] for item in actions],
            caseSensitive=False,
        )
        self.environment[
            oreportscons.ToolEnv.ACTION
        ] = next(
            item[1]['name']
            for item in actions
            if item[0] == res
        )


# vim: expandtab tabstop=4 shiftwidth=4
