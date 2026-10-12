<?php
/**
 * Visual search dialog. Populated by assets/js/visual-search.js.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;
?>
<div class="vsw-overlay" data-vsw-overlay hidden>
	<div class="vsw-dialog" role="dialog" aria-modal="true" aria-labelledby="vsw-title">
		<header class="vsw-head">
			<h2 id="vsw-title"><?php esc_html_e( 'Search by photo', 'visual-search-for-woocommerce' ); ?></h2>
			<button type="button" class="vsw-close" data-vsw-close aria-label="<?php esc_attr_e( 'Close', 'visual-search-for-woocommerce' ); ?>">&times;</button>
		</header>

		<div class="vsw-step vsw-pick" data-vsw-step="pick">
			<label class="vsw-drop" data-vsw-drop>
				<input type="file" accept="image/jpeg,image/png,image/webp" data-vsw-file hidden>
				<strong><?php esc_html_e( 'Drop a photo here or choose one', 'visual-search-for-woocommerce' ); ?></strong>
				<span><?php esc_html_e( 'JPG, PNG or WebP · up to 10 MB', 'visual-search-for-woocommerce' ); ?></span>
			</label>
			<button type="button" class="vsw-camera" data-vsw-camera><?php esc_html_e( 'Take a photo', 'visual-search-for-woocommerce' ); ?></button>
		</div>

		<div class="vsw-step vsw-analyze" data-vsw-step="analyze" hidden>
			<div class="vsw-preview">
				<img alt="" data-vsw-preview>
				<div class="vsw-boxes" data-vsw-boxes></div>
			</div>
			<p class="vsw-status" data-vsw-status aria-live="polite"></p>
			<div class="vsw-chips" data-vsw-chips role="listbox" aria-label="<?php esc_attr_e( 'Detected items', 'visual-search-for-woocommerce' ); ?>"></div>
			<button type="button" class="vsw-link" data-vsw-reset><?php esc_html_e( 'Use another photo', 'visual-search-for-woocommerce' ); ?></button>
		</div>

		<div class="vsw-results" data-vsw-results></div>
	</div>
</div>
