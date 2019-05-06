set terminal png size 900,400
set title "RUBBoS [FILL IN: WORKLOAD SIZE]"
set ylabel "Total CPU (%)"
set xlabel "Time (seconds)"
set xdata time
set timefmt "%s"
set format x "%s"
set key left top
set grid
plot "cpu0.data" using 1:2 with lines title "CPU 0", \
     "cpu1.data" using 1:2 with lines title "CPU 1"
