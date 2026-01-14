from newsplease import NewsPlease
article = NewsPlease.from_url('https://time.com/7345598/venezuela-militias-violence-maduro-trump/')
if article and hasattr(article, 'title') and article.title:
    print(article.title)
else:
    print("Failed to extract article title")