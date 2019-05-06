set terminal png size 900,400
set title "RUBBoS"
set ylabel "Response Time (milliseconds)"
set xlabel "Time (seconds)"
set xdata time
set timefmt "%s"
set format x "%s"
set key left top
set grid
plot "response_time.data" using 1:2 with lines title "Workload: [FILL IN: WORKLOAD SIZE]"
