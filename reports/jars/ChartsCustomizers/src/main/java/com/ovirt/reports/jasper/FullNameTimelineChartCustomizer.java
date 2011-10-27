package com.ovirt.reports.jasper;


import java.awt.BasicStroke;
import java.awt.Shape;
import java.awt.geom.Rectangle2D;
import java.text.DecimalFormat;
import java.text.SimpleDateFormat;
import org.jfree.chart.JFreeChart;
import org.jfree.chart.LegendItem;
import org.jfree.chart.LegendItemCollection;
import org.jfree.chart.axis.DateAxis;
import org.jfree.chart.axis.DateTickMarkPosition;
import org.jfree.chart.axis.DateTickUnit;
import org.jfree.chart.axis.NumberAxis;
import org.jfree.chart.axis.ValueAxis;
import org.jfree.chart.block.BlockBorder;
import org.jfree.chart.plot.XYPlot;
import org.jfree.chart.renderer.xy.XYItemRenderer;
import net.sf.jasperreports.engine.JRChart;
import net.sf.jasperreports.engine.JRChartCustomizer;

public class FullNameTimelineChartCustomizer implements JRChartCustomizer {

	public void customize(JFreeChart chart, JRChart jasperChart) {
			long longerThanMonthInMiliseconds = 3064800000L;
			XYPlot categoryPlot = chart.getXYPlot();
			XYItemRenderer renderer = chart.getXYPlot().getRenderer();
			
			categoryPlot.setNoDataMessage("No Data Available");
			DateAxis domainaxis = (DateAxis) categoryPlot.getDomainAxis();
	        domainaxis.setAutoTickUnitSelection(false);
	        if (domainaxis.getMaximumDate().getTime() - domainaxis.getMinimumDate().getTime() < longerThanMonthInMiliseconds) 
	        {
	        	domainaxis.setTickUnit(new DateTickUnit(DateTickUnit.DAY,5,new SimpleDateFormat("dd MMM")));
	        }
	        else
	        {
	        	domainaxis.setTickUnit(new DateTickUnit(DateTickUnit.DAY,14,new SimpleDateFormat("dd MMM")));
	        }
	        domainaxis.setTickMarkPosition(DateTickMarkPosition.START);
	        domainaxis.setTickMarksVisible(true);
	        domainaxis.setDateFormatOverride(new SimpleDateFormat("dd MMM"));
	        domainaxis.setLabelAngle(Math.PI / 2);
	        domainaxis.setLabelAngle(0);
	        
	        LegendItemCollection chartLegend = categoryPlot.getLegendItems();
	        LegendItemCollection res = new LegendItemCollection();
	        Shape square = new Rectangle2D.Double(0,0,5,5);
	        for (int i = 0; i < chartLegend.getItemCount(); i++) {
	           LegendItem item = chartLegend.get(i);
	           String label = item.getLabel();
	           if (label.trim() != "")
	           {
	        	   res.add(new LegendItem(label, item.getDescription(), item.getToolTipText(), item.getURLText(), true, square, true, item.getFillPaint(), item.isShapeOutlineVisible(), item.getOutlinePaint(), item.getOutlineStroke(), false, item.getLine(), item.getLineStroke(), item.getLinePaint()));
	           }
	           else {renderer.setSeriesVisibleInLegend(item.getSeriesIndex(),false);}
	        }
	        categoryPlot.setFixedLegendItems(res);	
	        chart.getLegend().setFrame(BlockBorder.NONE);
	        
	        renderer.setBaseStroke(

	        		new BasicStroke(2.0f, BasicStroke.JOIN_ROUND, BasicStroke.JOIN_BEVEL)

	        		);
	        
			ValueAxis rangeAxis = categoryPlot.getRangeAxis();
			if (rangeAxis instanceof NumberAxis) { 
				NumberAxis axis = (NumberAxis) rangeAxis;
				axis.setNumberFormatOverride(new DecimalFormat("###,###,###.#"));
				double upperBound = axis.getUpperBound();
				int a = (((int) upperBound / 10) * 10) + 10;
				upperBound = (double) a;
				axis.setUpperBound(upperBound);
				double lowerBound = axis.getLowerBound();
				int a2 = (((int) lowerBound / 10) * 10) - 10;
				lowerBound = (double) a2;
				if (lowerBound < (double) 0)
				{
					axis.setLowerBound((double) 0);
				}
				else 
				{
					axis.setLowerBound(lowerBound);
				}
				axis.setAutoRangeMinimumSize(1.0);
			}
			rangeAxis.setTickLabelsVisible(true);		
	}
}