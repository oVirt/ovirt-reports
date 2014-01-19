package org.ovirt.jasperreports.querymodifier;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Locale;
import java.util.Map;

import org.apache.commons.lang.StringUtils;

import com.jaspersoft.jasperserver.api.engine.common.service.IQueryManipulator;
import com.jaspersoft.jasperserver.war.common.JasperServerUtil;

public class CustomOvirtReportsQueryManipulator implements IQueryManipulator {
    public final static String USERLOCALE = "$P{userlocale}";
    public final static String DATETIMELOCALIZEDPATTERN = "$P{datetimelocalepattern}";
    public final static String DATELOCALIZEDPATTERN = "$P{datelocalepattern}";

    public IQueryManipulator cascading;

    @SuppressWarnings("rawtypes")
    @Override
    public String updateQuery(String query, Map parameters) {
        String cascadingQuery = cascading.updateQuery(query, parameters);
        Locale locale = JasperServerUtil.getExecutionContext().getLocale();
        String userLocale = locale.toString();
        String dateTimeLocalizedpatteren = getPostgresDatePatternString(locale, true);
        String dateLocalizedpatteren = getPostgresDatePatternString(locale, false);

        cascadingQuery = cascadingQuery.replace(USERLOCALE, "'" + userLocale + "'");
        cascadingQuery = cascadingQuery.replace(DATETIMELOCALIZEDPATTERN, "'" + dateTimeLocalizedpatteren + "'");
        cascadingQuery = cascadingQuery.replace(DATELOCALIZEDPATTERN, "'" + dateLocalizedpatteren + "'");
        return cascadingQuery;
    }

    public String getPostgresDatePatternString(Locale locale, Boolean time) {
        SimpleDateFormat dateLocalizedPattern;
        if (time) {
            dateLocalizedPattern = (SimpleDateFormat)SimpleDateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT, locale);
        }
        else {
            dateLocalizedPattern = (SimpleDateFormat)SimpleDateFormat.getDateInstance(DateFormat.SHORT, locale);
        }
        String dateLocalizedPatternString = dateLocalizedPattern.toPattern();
        /*year changes*/
        dateLocalizedPatternString = dateLocalizedPatternString.replace("y", "Y");
        /*day changes*/
        if (StringUtils.countMatches(dateLocalizedPatternString, "M") == 1) {
            dateLocalizedPatternString = dateLocalizedPatternString.replace("M", "MM");
        }
        /*day changes*/
        if (StringUtils.countMatches(dateLocalizedPatternString, "d") == 1) {
            dateLocalizedPatternString = dateLocalizedPatternString.replace("d", "dd");
        }
        dateLocalizedPatternString = dateLocalizedPatternString.replace("dd", "DD");
        /*hour changes*/
        if (StringUtils.countMatches(dateLocalizedPatternString, "H") == 1) {
            dateLocalizedPatternString = dateLocalizedPatternString.replace("H", "HH");
        }
        dateLocalizedPatternString = dateLocalizedPatternString.replace("HH", "HH24");
        if (StringUtils.countMatches(dateLocalizedPatternString, "h") == 1) {
            dateLocalizedPatternString = dateLocalizedPatternString.replace("h", "hh");
        }
        dateLocalizedPatternString = dateLocalizedPatternString.replace("hh", "HH12");
        /*minute changes*/
        dateLocalizedPatternString = dateLocalizedPatternString.replace("mm", "MI");
        /*second changes*/
        dateLocalizedPatternString = dateLocalizedPatternString.replace("ss", "SS");
        /*am\pm changes*/
        if (StringUtils.countMatches(dateLocalizedPatternString, "a") == 1) {
            dateLocalizedPatternString = dateLocalizedPatternString.replace("a", "aa");
        }
        dateLocalizedPatternString = dateLocalizedPatternString.replace("aa", "AM");
        return dateLocalizedPatternString;
    }

    public IQueryManipulator getCascading() {
        return cascading;
    }

    public void setCascading(IQueryManipulator cascading) {
        this.cascading = cascading;
    }
}
