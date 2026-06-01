SELECT 
    w.wallet_address AS address,
    e.name AS domain_name
FROM dune.lionrr08081045.dataset_unique_wallet_addresses w
LEFT JOIN labels.ens e 
    ON w.wallet_address = e.address
