package com.ovirt.reports.jasper;

import net.sf.jasperreports.engine.JRChart;
import net.sf.jasperreports.engine.JRChartCustomizer;

import org.jfree.chart.JFreeChart;
//import org.jfree.chart.block.BlockBorder;
import org.jfree.chart.labels.StandardPieSectionLabelGenerator;
import org.jfree.chart.plot.*;

//import java.awt.Shape;
//import java.awt.geom.Rectangle2D;

import org.jfree.chart.plot.PiePlot;


public class PieChartCustomizer implements JRChartCustomizer {

    public PieChartCustomizer() {
    }

    public void customize(JFreeChart chart, JRChart jasperChart) {
        Plot plot = chart.getPlot();

        plot.setNoDataMessage("No Data Available");
        chart.removeLegend();

        //Shape square = new Rectangle2D.Double(0,0,5,5);
        PiePlot piePlot = (PiePlot) plot;
        piePlot.setSimpleLabels(true);
        piePlot.setLabelGenerator(new StandardPieSectionLabelGenerator("{0}: {1} ({2})"));
        //piePlot.setLabelGenerator(null);
        //piePlot.setLegendLabelGenerator(new StandardPieSectionLabelGenerator("{0}: {1} ({2})"));
        //piePlot.setLegendItemShape(square);
        //chart.getLegend().setFrame(BlockBorder.NONE);
    }
}
