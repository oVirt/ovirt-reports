package com.ovirt.reports.jasper;

import java.awt.Color;

import org.jfree.chart.JFreeChart;

import net.sf.jasperreports.engine.JRChart;
import net.sf.jasperreports.engine.JRChartCustomizer;

import org.jfree.chart.axis.CategoryAxis;
import org.jfree.chart.axis.ValueAxis;
import org.jfree.chart.plot.CategoryPlot;
import org.jfree.chart.renderer.category.StackedBarRenderer;

public class HorizontalStackedBarChart implements JRChartCustomizer {

	public void customize(JFreeChart chart, JRChart jasperChart) {
		StackedBarRenderer renderer = (StackedBarRenderer) chart.getCategoryPlot().getRenderer();
		CategoryPlot categoryPlot = renderer.getPlot();
		renderer.setDrawBarOutline(true);
		renderer.setSeriesOutlinePaint(0, Color.black);
		renderer.setSeriesOutlinePaint(1, Color.black);
		renderer.setSeriesOutlinePaint(2, Color.black);
		renderer.setSeriesOutlinePaint(3, Color.black);
		
		CategoryAxis domainaxis = categoryPlot.getDomainAxis();
        domainaxis.setVisible(false);


		ValueAxis rangeAxis = categoryPlot.getRangeAxis();
		rangeAxis.setVisible(false);
	}
}