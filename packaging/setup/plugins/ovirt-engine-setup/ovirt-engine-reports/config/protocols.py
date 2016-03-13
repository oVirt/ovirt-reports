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


"""Protocols plugin."""


import gettext

from otopi import constants as otopicons
from otopi import filetransaction
from otopi import plugin
from otopi import util

from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """Protocols plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
    )
    def _misc(self):
        def flag(o):
            return 'true' if o else 'false'
        content = (
            'REPORTS_PROXY_ENABLED={proxyFlag}\n'
            'REPORTS_PROXY_HTTP_PORT={proxyHttpPort}\n'
            'REPORTS_PROXY_HTTPS_PORT={proxyHttpsPort}\n'
            'REPORTS_AJP_ENABLED={proxyFlag}\n'
            'REPORTS_AJP_PORT={ajpPort}\n'
            'REPORTS_HTTP_ENABLED={directFlag}\n'
            'REPORTS_HTTPS_ENABLED={directFlag}\n'
            'REPORTS_HTTP_PORT={directHttpPort}\n'
            'REPORTS_HTTPS_PORT={directHttpsPort}\n'
        ).format(
            proxyFlag=flag(self.environment[
                oreportscons.ConfigEnv.JBOSS_AJP_PORT
            ]),
            directFlag=flag(self.environment[
                oreportscons.ConfigEnv.JBOSS_DIRECT_HTTP_PORT
            ]),
            proxyHttpPort=self.environment[
                oreportscons.ConfigEnv.HTTP_PORT
            ],
            proxyHttpsPort=self.environment[
                oreportscons.ConfigEnv.HTTPS_PORT
            ],
            directHttpPort=self.environment[
                oreportscons.ConfigEnv.JBOSS_DIRECT_HTTP_PORT
            ],
            directHttpsPort=self.environment[
                oreportscons.ConfigEnv.JBOSS_DIRECT_HTTPS_PORT
            ],
            ajpPort=self.environment[
                oreportscons.ConfigEnv.JBOSS_AJP_PORT
            ],
        )

        if self.environment[osetupcons.CoreEnv.DEVELOPER_MODE]:
            content += (
                'REPORTS_DEBUG_ADDRESS={debugAddress}\n'
            ).format(
                debugAddress=self.environment[
                    oreportscons.ConfigEnv.JBOSS_DEBUG_ADDRESS
                ],
            )

        self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
            filetransaction.FileTransaction(
                name=(
                    oreportscons.FileLocations.
                    REPORTS_CONFIG_PROTOCOLS
                ),
                content=content,
                modifiedList=self.environment[
                    otopicons.CoreEnv.MODIFIED_FILES
                ],
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4
