set terminal png size 900,400
set title "RUBBoS [FILL IN: WORKLOAD SIZE]"
set ylabel "Memory usage (%)"
set xlabel "Time (seconds)"
set xdata time
set timefmt "%s"
set format x "%s"
set key left top
set grid
plot "mem.data" using 1:2 with lines title "Memory"
