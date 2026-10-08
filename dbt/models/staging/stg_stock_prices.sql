-- One row per ticker per trading day, with clean names.
select
    upper(ticker) || '|' || price_date::text as price_key,
    upper(ticker)                            as ticker,
    price_date,
    open                                     as open_usd,
    high                                     as high_usd,
    low                                      as low_usd,
    close                                    as close_price_usd,
    volume
from {{ source('raw', 'stock_prices') }}
