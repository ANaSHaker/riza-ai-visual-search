=== Visual Search for WooCommerce ===
Contributors: anashaker
Tags: visual search, image search, woocommerce, similar products, ai
Requires at least: 6.0
Tested up to: 6.6
Requires PHP: 7.4
Stable tag: 2.0.0
License: MIT

"Search by photo" and "similar items" for any WooCommerce store, powered by a self-hosted FashionCLIP + FAISS API.

== Description ==

Shoppers upload or take a photo. The plugin asks the visual search API to detect the items in it (dress, shoes, bag…),
lets the shopper tap one, and shows the most similar products from your catalogue. The same index powers a
"similar items" grid on product pages.

* Camera button for the product search form, or the `[vsw_visual_search]` shortcode
* `[vsw_similar_products id="123" limit="8" title="You may also like"]`
* Optional automatic "similar items" section on single product pages
* Auto-indexing on product save; vectors removed on trash/delete
* One-click batch indexing from the settings page
* REST routes for mobile apps: `POST /wp-json/vsw/v1/detect`, `POST /wp-json/vsw/v1/search`, `GET /wp-json/vsw/v1/similar/{id}`
* Templates can be overridden in `yourtheme/visual-search-for-woocommerce/`

The visual search API is a separate Python service (see the `api/` folder of this repository). Run it on the same server
or a private network and protect it with an API key.

== Installation ==

1. Upload the `visual-search-for-woocommerce` folder to `/wp-content/plugins/` and activate it.
2. Go to WooCommerce → Visual Search, enter the API URL and API key, and save.
3. Click "Start indexing".

== Security ==

* Uploaded photos are type-sniffed, limited to 10 MB, stored under random names in a non-public folder and deleted after 30 minutes.
* Public routes are rate-limited per visitor.
* Only published, visible products are ever returned.
* Admin actions require the `manage_woocommerce` capability and a nonce. The API key is never printed back into the page.

== Changelog ==

= 2.0.0 =
* Rewrite as a standalone, store-agnostic plugin: Settings API, REST controller, upload store, indexer, shortcodes, templates.
