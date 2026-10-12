<?php
/**
 * Turns API hits (product id + score) into storefront-safe product cards.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

class VSW_Product_Presenter {

	/**
	 * Keep only products that are published, visible and above the score
	 * cut-off, preserving the API's order.
	 *
	 * @param array $hits      API results.
	 * @param float $min_score Storefront similarity cut-off.
	 * @param int   $limit     Max products.
	 * @return array<int, array>
	 */
	public function present( array $hits, $min_score, $limit ) {
		$out = array();
		foreach ( $hits as $hit ) {
			if ( count( $out ) >= $limit ) {
				break;
			}
			$score = isset( $hit['score'] ) ? (float) $hit['score'] : 0.0;
			if ( $score < $min_score ) {
				continue;
			}
			$product = wc_get_product( absint( $hit['product_id'] ?? 0 ) );
			if ( ! $product || 'publish' !== $product->get_status() || ! $product->is_visible() ) {
				continue;
			}
			$out[] = $this->card( $product, $score );
		}
		return $out;
	}

	/**
	 * @param WC_Product $product Product.
	 * @param float      $score   Similarity.
	 */
	public function card( $product, $score = null ) {
		$image_id = $product->get_image_id();
		return array(
			'id'         => $product->get_id(),
			'name'       => wp_strip_all_tags( $product->get_name() ),
			'url'        => esc_url_raw( get_permalink( $product->get_id() ) ),
			'image'      => esc_url_raw( $image_id ? wp_get_attachment_image_url( $image_id, 'woocommerce_thumbnail' ) : wc_placeholder_img_src( 'woocommerce_thumbnail' ) ),
			'price_html' => wp_kses_post( $product->get_price_html() ),
			'on_sale'    => $product->is_on_sale(),
			'in_stock'   => $product->is_in_stock(),
			'score'      => null === $score ? null : round( (float) $score, 3 ),
		);
	}
}
