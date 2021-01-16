# Scrapers
> Web scraping scripts to generate data sets for Machine Learning.

- [Myntra](myntra.py) -> 
    > fetch clothing images from www.myntra.com & organize them into seperate folders per category & gender  
    - Employs multiprocessing to speed up data retrieval  
    - Metadata of downloaded images would be available at ./data/productData.csv post the script execution  
    - Update `search_strings`, `sort_options`, `page_limit` as per requirements