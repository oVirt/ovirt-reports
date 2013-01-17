<%--
  ~ Copyright (C) 2005 - 2011 Jaspersoft Corporation. All rights reserved.
  ~ http://www.jaspersoft.com.
  ~
  ~ Unless you have purchased  a commercial license agreement from Jaspersoft,
  ~ the following license terms  apply:
  ~
  ~ This program is free software: you can redistribute it and/or  modify
  ~ it under the terms of the GNU Affero General Public License  as
  ~ published by the Free Software Foundation, either version 3 of  the
  ~ License, or (at your option) any later version.
  ~
  ~ This program is distributed in the hope that it will be useful,
  ~ but WITHOUT ANY WARRANTY; without even the implied warranty of
  ~ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
  ~ GNU Affero  General Public License for more details.
  ~
  ~ You should have received a copy of the GNU Affero General Public  License
  ~ along with this program. If not, see <http://www.gnu.org/licenses/>.
  --%>

<%@ page contentType="text/html" %>

<%
    response.setHeader("P3P","CP='IDC DSP COR ADM DEVi TAIi PSA PSD IVAi IVDi CONi HIS OUR IND CNT'");
%>

<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c"%>
<%@ taglib uri="http://java.sun.com/jsp/jstl/functions" prefix="fn"%>
<%@ taglib uri="/spring" prefix="spring"%>
<%@ taglib uri="/WEB-INF/jasperserver.tld" prefix="js" %>
<%@ taglib prefix="tiles" uri="http://tiles.apache.org/tags-tiles" %>

<%@ page import="org.apache.commons.lang.StringEscapeUtils" %>
<%@ page import="com.jaspersoft.jasperserver.war.webHelp.WebHelpLookup" %>
<%@ page import="com.jaspersoft.jasperserver.api.engine.common.service.impl.NavigationActionModelSupport" %>

<html>
    <head>
        <title>RHEVM Reports: <decorator:title /></title>
        <meta http-equiv="Content-Type" content="text/html; charset=${requestScope['com.jaspersoft.ji.characterEncoding']}">
		<meta http-equiv="X-UA-Compatible" content="IE=8"/>
		<link rel="shortcut icon" href="favicon.ico" />
        <%@ include file="decoratorCommonImports.jsp" %>
        <decorator:head />
        <%--Online Help--%>
        <%@ include file="../jsp/modules/webHelp/webHelp.jsp" %>
    </head>

<c:choose>
    <c:when test="${param['nui'] == null}">
    <%@ include file="../jsp/modules/common/jsEdition.jsp" %>

    <body id="<decorator:getProperty property='body.id'/>" class="<decorator:getProperty property='body.class'/>">
    <div id="banner" class="banner">
        <div id="systemMessageConsole" style="display:none;">
            <p id="systemMessage"><spring:message code="button.close"/></p>
        </div>
        <div id="logo" class="sectionLeft"></div>
        <div class="sectionLeft" style="position:relative;z-index:1;">
            <c:if test="${pageProperties['meta.noMenu']==null}">
               <div id="mainNavigation" class="menu horizontal primaryNav">
                   <ul id="navigationOptions" data-tab-index="2" data-component-type="navigation">
                       <li id="main_home" tabIndex="-1" class="leaf"><p class="wrap button"><span class="icon"></span><spring:message code="menu.home"/></p></li>
                       <li id="main_library" tabIndex="-1" class="leaf"><p class="wrap button"><span class="icon"></span><spring:message code="menu.library"/></p></li>
                   </ul>
               </div>
             </c:if>
        </div>
        <div class="sectionRight searchContainer">
            <!-- banner search -->
            <t:insertTemplate template="/WEB-INF/jsp/templates/control_searchLockup.jsp">
                <t:putAttribute name="containerID" value="globalSearch"/>
                <t:putAttribute name="containerAttr" value="data-tab-index='1' data-component-type='search'"/>
                <t:putAttribute name="inputID" value="searchInput"/>
            </t:insertTemplate>
        </div>
        <ul id="metaLinks" class="sectionRight">
            <li id="userID">
                <authz:authorize ifNotGranted="ROLE_ANONYMOUS">
			            <span id="casted">
			                <c:if test="<%= com.jaspersoft.jasperserver.api.metadata.user.service.impl.UserAuthorityServiceImpl.isUserSwitched() %>">
                                <%= ((com.jaspersoft.jasperserver.api.metadata.user.domain.User)
                                        com.jaspersoft.jasperserver.api.metadata.user.service.impl.UserAuthorityServiceImpl.
                                                getSourceAuthentication().getPrincipal()).getFullName() %>
                                <spring:message code="jsp.main.as"/>
                            </c:if>
			            </span>
                    <authz:authentication property="principal.fullName"/>
                </authz:authorize>
            </li>
            <c:set var="isShowHelp" scope="page"><%= WebHelpLookup.getInstance().isShowHelpTrue() %></c:set>
            <c:if test="${isProVersion && isShowHelp}"><li id="help"><a href="#" id="helpLink"><spring:message code="decorator.helpLink"/></a></li></c:if>
            <li id="main_logOut" class="last"><a id="main_logOut_link" href="exituser.html"><spring:message code="menu.logout"/></a></li>
        </ul>
    </div>

    <div id="frame">
        <div class="content">
            <decorator:body />
        </div>
    </div>

    <div id="frameFooter">
        <a id="about" href="#"><spring:message code="decorator.aboutLink"/></a>
        <div id="hb" style="position:absolute;top:1px;left:260px;background:#fff;color#333;"></div>
        <p id="copyright"><spring:message code="decorators.main.copyright"/></p>
    </div>

    <div id="templateElements">
        <%@ include file="decoratorMinimalComponents.jsp" %>
        <%@ include file="../jsp/modules/commonJSTLScripts.jsp" %>
        <div style="display:none">
            <p class="action">&nbsp;</p>
            <p class="action over">&nbsp;</p>
            <p class="action pressed">&nbsp;</p>
            <p class="action primary">&nbsp;</p>
            <p class="action primary over">&nbsp;</p>
            <p class="action primary pressed">&nbsp;</p>
        </div>
    </div>
    </body>
    </c:when>
    <c:otherwise>
    <body id="<decorator:getProperty property='body.id'/>" class="<decorator:getProperty property='body.class'/>">
		<a class="offLeft" href="#maincontent">Skip to main content</a>
        <%@ include file="decoratorCommonComponents.jsp" %>

        <div id="frame" class="column decorated">
            <tiles:insertTemplate template="/WEB-INF/jsp/templates/utility_cosmetic.jsp"/>
            <div class="content">
               <div class="header">
                   <span class="cosmetic"></span>
                   <%--
                       We can cancel menu generation by passing following meta tag:
                       <meta name="noMenu" content="true">

                       This is necessary for example in analysis drill-down pop-up
                   --%>
                   <c:if test="${pageProperties['meta.noMenu']==null}">
                       <div id="mainNavigation" class="menu horizontal primaryNav">
                           <ul id="navigationOptions" data-tab-index="2" data-component-type="navigation">
                               <li id="main_home" tabIndex="-1" class="leaf"><p class="wrap button"><span class="icon"></span><spring:message code="menu.home"/></p></li>
                               <li id="main_library" tabIndex="-1" class="leaf"><p class="wrap button"><span class="icon"></span><spring:message code="menu.library"/></p></li>
                           </ul>
                       </div>
                   </c:if>
               </div><!--/#frame .header -->

            <!-- START decorated page content-->
            <decorator:body />
            <!-- END decorated page content -->

                <!-- <div class="footer"></div> --><!--/#frame .footer -->
            </div><!--/#frame .content -->
        </div><!--/#frame -->
        <div id="footer" class="footer">
            <a id="about" href="#"><spring:message code="decorator.aboutLink"/></a>
            <p id="copyright"><spring:message code="decorators.main.copyright"/></p>
        </div>

        <div id="systemMessageConsole" style="display:none;">
            <p id="systemMessage" style="padding:4px;color:#fff;"></p>
        </div>

        <%--JavaScript which is common to all pages and requires JSTL access--%>
        <%@ include file="../jsp/modules/commonJSTLScripts.jsp" %>
    </body>
    </c:otherwise>
</c:choose>
</html>





