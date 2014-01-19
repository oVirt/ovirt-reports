package com.ovirt.reports.jasper;

import java.awt.Color;


import net.sf.jasperreports.engine.JRChart;
import net.sf.jasperreports.engine.JRChartCustomizer;

import org.jfree.chart.JFreeChart;
//import org.jfree.chart.block.BlockBorder;
import org.jfree.chart.labels.StandardPieSectionLabelGenerator;
import org.jfree.chart.plot.*;

//import java.awt.Shape;
//import java.awt.geom.Rectangle2D;

import org.jfree.chart.plot.PiePlot;


public class TimePieChartCustomizer implements JRChartCustomizer {

    public TimePieChartCustomizer() {
    }

    public void customize(JFreeChart chart, JRChart jasperChart) {
        Plot plot = chart.getPlot();

        plot.setNoDataMessage("No Data Available");
        chart.removeLegend();

        //Shape square = new Rectangle2D.Double(0,0,5,5);
        PiePlot piePlot = (PiePlot) plot;
        piePlot.setSimpleLabels(true);
        piePlot.setLabelGenerator(new StandardPieSectionLabelGenerator("{0} ({2})"));
        float[] green = new float[3];
        float[] red = new float[3];
        Color.RGBtoHSB(255, 0, 0, red);
        Color.RGBtoHSB(111, 191, 0, green);
        for (int i = 1; i <= piePlot.getDataset().getItemCount(); i++)
        {
                if (piePlot.getDataset().getKey(i-1).toString().contains("Above".subSequence(0, 4)))
                {
                    piePlot.setSectionPaint(piePlot.getDataset().getKey(i-1), Color.getHSBColor(red[0], red[1], red[2]));
                }
                if  (piePlot.getDataset().getKey(i-1).toString().contains("Below".subSequence(0, 4)))
                {
                    piePlot.setSectionPaint(piePlot.getDataset().getKey(i-1), Color.getHSBColor(green[0], green[1], green[2]));
                }
        }
        //piePlot.setLabelGenerator(null);
        //piePlot.setLegendLabelGenerator(new StandardPieSectionLabelGenerator("{0} ({2})"));
        //piePlot.setLegendItemShape(square);
        //chart.getLegend().setFrame(BlockBorder.NONE);
    }
}
