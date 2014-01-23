#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2013 Red Hat, Inc.
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
from ovirt_engine_setup import reportsconstants as oreportscons


@util.export
class Plugin(plugin.PluginBase):

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
        after=(
            osetupcons.Stages.DB_CONNECTION_AVAILABLE,
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

        with open(oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_UI) as f:
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=os.path.join(
                        osetupcons.FileLocations.OVIRT_ENGINE_LOCALSTATEDIR,
                        'reports.xml',
                    ),
                    content=f.read(),
                    modifiedList=uninstall_files,
                )
            )

        self.environment[osetupcons.DBEnv.STATEMENT].updateVdcOptions(
            options=(
                {
                    'name': 'RedirectServletReportsPage',
                    'value': '/ovirt-engine-reports',
                },
            ),
        )


# vim: expandtab tabstop=4 shiftwidth=4
