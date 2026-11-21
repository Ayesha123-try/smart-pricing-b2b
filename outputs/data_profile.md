# Data profile

## row counts

```
       t    n
pipeline 8800
accounts   85
products    7
   teams   35
```

## duplicate opportunity ids

```
 dupes
     0
```

## stages and close_value

```
 deal_stage    n  has_engage  has_close  has_value  value_zero  value_pos  has_account
        Won 4238        4238       4238       4238         0.0     4238.0         4238
       Lost 2473        2473       2473       2473      2473.0        0.0         2473
   Engaging 1589        1589          0          0         0.0        0.0          501
Prospecting  500           0          0          0         0.0        0.0          163
```

## date ranges

```
 deal_stage    min_eng    max_eng  min_close  max_close
   Engaging 2016-11-03 2017-12-22        NaT        NaT
        Won 2016-10-20 2017-12-27 2017-03-01 2017-12-31
       Lost 2016-11-04 2017-12-22 2017-03-01 2017-12-31
Prospecting        NaT        NaT        NaT        NaT
```

## products with no match in products table

```
product    n
 GTXPro 1480
```

## accounts with no match in accounts table

```
account  deal_stage    n
   None    Engaging 1088
   None Prospecting  337
```

## agents with no match in teams table

```
 n
 0
```

## sectors

```
            sector  n
        employment  4
     entertainment  6
           finance  8
         marketing  8
           medical 12
            retail 17
          services  5
          software  7
         technolgy 12
telecommunications  6
```

## won value vs list price by product

```
       product  list_price  won  min_v      p25     p50      p75  max_v  avg_ratio_to_list
    MG Special          55  793     38    52.00    55.0    59.00     72              1.004
     GTX Basic         550  915    365   511.00   547.0   582.00    716              0.992
GTX Plus Basic        1096  653    752  1011.00  1083.0  1155.00   1374              0.985
   MG Advanced        3393  654   2477  3164.25  3382.5  3624.75   4456              0.999
        GTXPro        4821  729   3169  4492.00  4828.0  5107.00   6166              0.999
  GTX Plus Pro        5482  479   3704  5084.50  5503.0  5863.50   7356              1.001
       GTK 500       26768   15  23746 25118.50 25897.0 28568.50  30288              0.998
```

## closed deals by month

```
      m   won  lost
2017-03 531.0 116.0
2017-04 285.0 301.0
2017-05 438.0 367.0
2017-06 531.0 110.0
2017-07 308.0 319.0
2017-08 446.0 339.0
2017-09 503.0 132.0
2017-10 279.0 287.0
2017-11 406.0 362.0
2017-12 511.0 140.0
```

## engaged deals by month

```
      m   won  lost  open
2016-10   7.0   0.0   0.0
2016-11  83.0  19.0  13.0
2016-12 160.0  36.0  40.0
2017-01 181.0  66.0  65.0
2017-02 277.0 143.0  95.0
2017-03 440.0 215.0 137.0
2017-04 427.0 326.0 121.0
2017-05 366.0 222.0 134.0
2017-06 453.0 228.0 111.0
2017-07 441.0 355.0 402.0
2017-08 341.0 198.0 254.0
2017-09 425.0 252.0 102.0
2017-10 400.0 303.0  58.0
2017-11 157.0  87.0  39.0
2017-12  80.0  23.0  18.0
```
