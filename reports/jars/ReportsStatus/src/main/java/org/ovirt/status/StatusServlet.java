package org.ovirt.status;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.io.PrintWriter;

public class StatusServlet extends HttpServlet {

  private static final String message = "Reports Webapp Deployed";

  public void doGet(HttpServletRequest request,
                    HttpServletResponse response)
            throws ServletException, IOException {
      response.setHeader("Access-Control-Allow-Origin","*");
      // Set response content type
      response.setContentType("text/html");

      // Actual logic goes here.
      PrintWriter out = response.getWriter();
      out.println(message);
  }

}

