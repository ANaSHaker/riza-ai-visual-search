<?php
/**
 * Keeps the visual index in sync with the WooCommerce catalogue.
 *
 * - On product save: fire-and-forget batch with the product's images.
 * - On trash/delete: remove the product's vectors.
 * - Admin "Start indexing": AJAX loop over all products, a few per request,
 *   so it never hits PHP time limits on shared hosting.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

class VSW_Indexer {

	const NONCE      = 'vsw_index';
	const BATCH_SIZE = 5;
	const MAX_IMAGES = 5;

	/** @var VSW_Settings */
	private $settings;
	/** @var VSW_Api_Client */
	private $api;

	public function __construct( VSW_Settings $settings, VSW_Api_Client $api ) {
		$this->settings = $settings;
		$this->api      = $api;
	}

	public function register() {
		add_action( 'woocommerce_update_product', array( $this, 'on_product_saved' ), 20 );
		add_action( 'woocommerce_new_product', array( $this, 'on_product_saved' ), 20 );
		add_action( 'wp_trash_post', array( $this, 'on_product_removed' ) );
		add_action( 'before_delete_post', array( $this, 'on_product_removed' ) );
		add_action( 'wp_ajax_vsw_index_batch', array( $this, 'ajax_index_batch' ) );
	}

	/**
	 * Image URLs (main + gallery) and category names for one product.
	 *
	 * @param WC_Product $product Product.
	 * @return array<int, array>
	 */
	public static function product_items( $product ) {
		$ids = array_filter( array_merge( array( $product->get_image_id() ), $product->get_gallery_image_ids() ) );
		$ids = array_slice( array_unique( array_map( 'absint', $ids ) ), 0, self::MAX_IMAGES );

		$categories = array();
		foreach ( $product->get_category_ids() as $term_id ) {
			$term = get_term( $term_id, 'product_cat' );
			if ( $term && ! is_wp_error( $term ) ) {
				$categories[] = html_entity_decode( $term->name, ENT_QUOTES, 'UTF-8' );
			}
		}

		$items = array();
		foreach ( $ids as $attachment_id ) {
			$url = wp_get_attachment_image_url( $attachment_id, 'woocommerce_single' );
			if ( $url ) {
				$items[] = array(
					'product_id' => $product->get_id(),
					'image_url'  => esc_url_raw( $url ),
					'categories' => $categories,
				);
			}
		}
		return $items;
	}

	/** @param int $product_id Product ID. */
	public function on_product_saved( $product_id ) {
		if ( ! $this->settings->get( 'auto_index' ) || wp_is_post_revision( $product_id ) ) {
			return;
		}
		$product = wc_get_product( $product_id );
		if ( ! $product || 'publish' !== $product->get_status() ) {
			return;
		}
		$items = self::product_items( $product );
		if ( $items ) {
			$this->api->index_batch( $items, false );
		}
	}

	/** @param int $post_id Post ID. */
	public function on_product_removed( $post_id ) {
		if ( 'product' === get_post_type( $post_id ) ) {
			$this->api->delete_product( $post_id );
		}
	}

	public function ajax_index_batch() {
		check_ajax_referer( self::NONCE, 'nonce' );
		if ( ! current_user_can( VSW_Settings::CAP ) ) {
			wp_send_json_error( array( 'message' => __( 'Not allowed.', 'visual-search-for-woocommerce' ) ), 403 );
		}
		if ( function_exists( 'set_time_limit' ) ) {
			@set_time_limit( 300 ); // phpcs:ignore WordPress.PHP.NoSilencedErrors
		}

		$offset = isset( $_POST['offset'] ) ? absint( wp_unslash( $_POST['offset'] ) ) : 0;
		$ids    = wc_get_products(
			array(
				'status'  => 'publish',
				'limit'   => self::BATCH_SIZE,
				'offset'  => $offset,
				'orderby' => 'ID',
				'order'   => 'ASC',
				'return'  => 'ids',
			)
		);

		if ( empty( $ids ) ) {
			$this->api->rebuild(); // compact the in-memory index after a full pass
			wp_send_json_success( array( 'done' => true ) );
		}

		$items = array();
		foreach ( $ids as $id ) {
			$product = wc_get_product( $id );
			if ( $product ) {
				$items = array_merge( $items, self::product_items( $product ) );
			}
		}

		$indexed = 0;
		$failed  = 0;
		if ( $items ) {
			$result = $this->api->index_batch( $items );
			if ( is_wp_error( $result ) ) {
				wp_send_json_error( array( 'message' => $result->get_error_message() ), 502 );
			}
			$indexed = (int) ( $result['indexed'] ?? 0 );
			$failed  = (int) ( $result['failed'] ?? 0 );
		}

		wp_send_json_success(
			array(
				'done'        => false,
				'indexed'     => $indexed,
				'failed'      => $failed,
				'next_offset' => $offset + count( $ids ),
			)
		);
	}
}
