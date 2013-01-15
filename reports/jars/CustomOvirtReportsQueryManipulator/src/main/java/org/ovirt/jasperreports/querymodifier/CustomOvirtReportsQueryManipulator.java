package org.ovirt.jasperreports.querymodifier;
import java.util.Locale;
import java.util.Map;

import com.jaspersoft.jasperserver.api.engine.common.service.IQueryManipulator;
import com.jaspersoft.jasperserver.war.common.JasperServerUtil;

public class CustomOvirtReportsQueryManipulator implements IQueryManipulator {
    public final static String USERLOCALE = "$P{userlocale}";

    public IQueryManipulator cascading;

    @SuppressWarnings("rawtypes")
    @Override
    public String updateQuery(String query, Map parameters) {
        String cascadingQuery = cascading.updateQuery(query, parameters);
        Locale locale = JasperServerUtil.getExecutionContext().getLocale();
        String userLocale = locale.toString();
        cascadingQuery = cascadingQuery.replace(USERLOCALE, "'" + userLocale + "'");
        return cascadingQuery;
    }

    public IQueryManipulator getCascading() {
        return cascading;
    }

    public void setCascading(IQueryManipulator cascading) {
        this.cascading = cascading;
    }
}
