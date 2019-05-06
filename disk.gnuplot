set terminal png size 900,400
set title "RUBBoS [FILL IN: WORKLOAD SIZE]"
set ylabel "Disk usage (in kB)"
set xlabel "Time (seconds)"
set xdata time
set timefmt "%s"
set format x "%s"
set key left top
set grid
plot "diskread.data" using 1:2 with lines title "Read", \
     "diskwrite.data" using 1:2 with lines title "Write"
