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


import gettext

from otopi import plugin
from otopi import util

from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.engine_common import constants as oengcommcons
from ovirt_engine_setup.reports import constants as oreportscons

from ovirt_setup_lib import dialog


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        name=oreportscons.Stages.CORE_ENABLE,
        before=(
            osetupcons.Stages.DIALOG_TITLES_E_PRODUCT_OPTIONS,
            oreportscons.Stages.DB_CONNECTION_CUSTOMIZATION,
        ),
        after=(
            osetupcons.Stages.DIALOG_TITLES_S_PRODUCT_OPTIONS,
        ),
    )
    def _customization(self):
        if self.environment[oreportscons.CoreEnv.ENABLE] is None:
            self.environment[
                oreportscons.CoreEnv.ENABLE
            ] = dialog.queryBoolean(
                dialog=self.dialog,
                name='OVESETUP_REPORTS_ENABLE',
                note=_(
                    'Configure Reports on this host '
                    '(@VALUES@) [@DEFAULT@]: '
                ),
                prompt=True,
                default=True,
            )
        if self.environment[oreportscons.CoreEnv.ENABLE]:
            self.environment[oengcommcons.ApacheEnv.ENABLE] = True
            self.environment[
                oreportscons.ConfigEnv.REPORTS_SERVICE_STOP_NEEDED
            ] = True

# vim: expandtab tabstop=4 shiftwidth=4
