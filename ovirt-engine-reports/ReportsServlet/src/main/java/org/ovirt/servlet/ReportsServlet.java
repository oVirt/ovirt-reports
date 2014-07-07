package org.ovirt.servlet;

import java.io.IOException;
import java.io.PrintWriter;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class ReportsServlet extends HttpServlet {

    private static final String COMMAND = "command";
    private static final String DEPLOYED_MSG = "Reports Webapp Deployed";
    private static final String STATUS = "status";
    private static final String XML = "webadmin-ui-xml";
    private static final String REPORTS_XML_URI = "/ovirt-engine-reports/reports.xml";

    public void doGet(HttpServletRequest request,
                      HttpServletResponse response)
            throws ServletException, IOException {
        response.setHeader("Access-Control-Allow-Origin", "*");

        String command = request.getParameter(COMMAND);
        if (command == null || command.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        } else {
            switch (command) {
                case STATUS:
                    // Set response content type
                    response.setContentType("text/html");
                    // Actual logic goes here.
                    PrintWriter out = response.getWriter();
                    out.println(DEPLOYED_MSG);
                    break;
                case XML:
                    response.sendRedirect(REPORTS_XML_URI);
                    break;
                default:
                    response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
                    break;
            }
        }
    }
}

