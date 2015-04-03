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


"""
Firewall configuration plugin for Reports.
"""


import gettext


from otopi import plugin
from otopi import util


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """
    Firewall configuration plugin for Engine
    """

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        after=(
            osetupcons.Stages.NET_FIREWALL_MANAGER_AVAILABLE,
        ),
    )
    def _configuration(self):
        self.environment[
            osetupcons.NetEnv.FIREWALLD_SUBST
        ].update({
            '@REPORTS_HTTP_PORT@': self.environment[
                oreportscons.ConfigEnv.JBOSS_DIRECT_HTTP_PORT
            ],
            '@REPORTS_HTTPS_PORT@': self.environment[
                oreportscons.ConfigEnv.JBOSS_DIRECT_HTTPS_PORT
            ],
        })
        if self.environment[
            oreportscons.ConfigEnv.JBOSS_DIRECT_HTTP_PORT
        ] is not None:
            self.environment[osetupcons.NetEnv.FIREWALLD_SERVICES].extend([
                {
                    'name': 'ovirt-reports-http',
                    'directory': 'reports'
                },
                {
                    'name': 'ovirt-reports-https',
                    'directory': 'reports'
                },
            ])


# vim: expandtab tabstop=4 shiftwidth=4
