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


from otopi import util


from . import admin
from . import engine
from . import firewall
from . import jasper
from . import jboss
from . import java
from . import protocols
from . import sso
from . import database


@util.export
def createPlugins(context):
    admin.Plugin(context=context)
    engine.Plugin(context=context)
    firewall.Plugin(context=context)
    jasper.Plugin(context=context)
    jboss.Plugin(context=context)
    java.Plugin(context=context)
    protocols.Plugin(context=context)
    sso.Plugin(context=context)
    database.Plugin(context=context)


# vim: expandtab tabstop=4 shiftwidth=4
