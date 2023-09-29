# Crawler

This is a browser based webcrawler based on scrapy and Playwright.

The main features are:

- Based on scrapy and Playwright
- supports dynamic page content
- Cleans up webpages using the [mozilla/readability](https://github.com/mozilla/readability). This the same as in Firefox Reader view.
- Can be easily extended or customized using python and playwright or scrapy
- Provides the full link structure of the crawling as well as the html version of the web page for later processing or analysis. This allows for example to do paragraph splitting based on the HTML view (e.g. Header) and not only on text.

## Setting up the project

- Install Poetry ([docs](https://python-poetry.org/docs/)):
  ```bash
  curl -sSL https://install.python-poetry.org | python3 -
  ```

* Make sure to add poetry to env [path](https://python-poetry.org/docs/#:~:text=Add%20Poetry%20to%20your%20PATH)

- Alternatively you can use brew

  ```bash
  brew install poetry
  ```

- Install required packages

  ```bash
  cd 01_crawler
  poetry install
  ```

- If you want to add a new package (optional)

  ```bash
  poetry add mypackage
  ```

- Enter poetry shell

  ```bash
  poetry shell
  ```

- Install browsers for playwright (from poetry shell)
  ```bash
  playwright install-deps
  playwright install
  ```

## Running the crawler,

- give the name, configuration and path for the output file, the file should be then used in **04_ingest_html_embeddings_to_opensearch.ipynb** notebook
  ```bash
  # user has to be in poetry shell
  cd crawly
  scrapy crawl webpage -O ../web-content/admin_ch_press_releases_en.json -a filename=configs/admin-ch-press-releases-en.json
  aws s3 cp admin_ch_press_releases_en.json s3://gen-ai-foundation/crawlers/admin-ch/
  scrapy crawl webpage -O ../web-content/admin_ch_press_releases_de.json -a filename=configs/admin-ch-press-releases-de.json
  aws s3 cp admin_ch_press_releases_de.json s3://gen-ai-foundation/crawlers/admin-ch/
  ```

## Debugging the crawler

There might be cases where you need to add some custom actions to the crawler, so that it can support specific webpages.
You can investigate the playwright actions by starting the automation recorder
`bash
    npx playwright codegen admin.ch
    `

- setup your IDE (VS Code)
  `json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Scrapy",
            "type": "python",
            "request": "launch",
            "python": "<YOUR_PYTHON_PATH>",
            "module": "scrapy",
            "args": [
                "crawl",
                "webpage",
                "-O", 
                "../web-content/admin_ch_press_releases_en.json",
                "-a",
                "filename=configs/admin-ch-press-releases-en.json"
            ],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}/01_crawler/crawly"
        }
    ]
}    
`
  ## Todo
- Download the files and update the ingestion notebook to consider them
