# About

A big bundle of requirements files from public GitHub repos.

# Files

Raw requirements data is in `data.json`. To read individual requirement files:

```
with open('data.json') as f:
    for line in f.readlines():
        data = json.loads(line)
```

A pre-processed index is available at `index.json`. It contains a breakdown of all individual requirements for a given package.

```
{
  "sqlalchemy": {
    "": 1662,
    "==0.9.3": 117,
    "<=0.9.99,>=0.9.7,>=0.8.4,<=0.8.99": 56,
    "==1.0.14": 189,
    "==1.0.9": 237,
    ">=1.0.4": 8,
    ">=0.9.7,<1.1.0": 121,
    "==1.0.13": 221,
    "==1.0.4": 629,
    ">=0.7": 24,
    ">=0.7.8,<=0.7.99": 69,
    "==1.1.6": 146,
    "==0.9.9": 498,
    "==0.9.8": 738,
    "==0.9.4": 318,
    "==1.0.8": 433,
    "==1.1.3": 113,
    "==0.7.6": 22
    ...
  }
  ...
}
```


# Query used
```
SELECT
 F.repo_name,
 F.path,
 C.content
FROM (
    SELECT
      repo_name,
      path,
      id
    FROM
      [bigquery-public-data:github_repos.files]
    WHERE
      REGEXP_MATCH (path, r'.*requirements.*\.(pip|txt)')
    )
    AS F

    JOIN [bigquery-public-data:github_repos.contents] as C
    ON F.ID = C.ID
```
