<?php
/**
 * Storefront output:
 *   [vsw_visual_search label="Search by photo"]   camera button + modal
 *   [vsw_similar_products id="123" limit="8"]     "similar items" grid
 * plus optional automatic placement (product search form, single product page).
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

class VSW_Shortcodes {

	const CACHE_TTL = 12 * HOUR_IN_SECONDS;

	/** @var VSW_Settings */
	private $settings;
	/** @var VSW_Api_Client */
	private $api;
	/** @var VSW_Product_Presenter */
	private $presenter;
	/** @var bool */
	private $modal_printed = false;

	public function __construct( VSW_Settings $settings, VSW_Api_Client $api, VSW_Product_Presenter $presenter ) {
		$this->settings  = $settings;
		$this->api       = $api;
		$this->presenter = $presenter;
	}

	public function register() {
		add_shortcode( 'vsw_visual_search', array( $this, 'visual_search' ) );
		add_shortcode( 'vsw_similar_products', array( $this, 'similar_shortcode' ) );

		if ( $this->settings->get( 'search_form_button' ) ) {
			add_filter( 'get_product_search_form', array( $this, 'append_to_search_form' ) );
		}
		if ( $this->settings->get( 'similar_on_product' ) ) {
			add_action( 'woocommerce_after_single_product_summary', array( $this, 'render_on_product_page' ), 25 );
		}
		add_action( 'wp_footer', array( $this, 'print_modal' ) );
	}

	/**
	 * Similar products for a product, cached per product in a transient so the
	 * API is called at most twice a day per product page.
	 *
	 * @return array<int, array>
	 */
	public static function similar_products( VSW_Api_Client $api, VSW_Product_Presenter $presenter, $product_id, $limit ) {
		$product_id = absint( $product_id );
		$limit      = max( 1, min( 24, (int) $limit ) );
		$cache_key  = 'vsw_similar_' . $product_id . '_' . $limit;
		$hits       = get_transient( $cache_key );

		if ( false === $hits ) {
			$data = $api->similar( $product_id, $limit * 3 );
			$hits = is_wp_error( $data ) ? array() : (array) ( $data['results'] ?? array() );
			set_transient( $cache_key, $hits, is_wp_error( $data ) ? 10 * MINUTE_IN_SECONDS : self::CACHE_TTL );
		}
		// Visibility/stock are re-checked on every render; only ids are cached.
		$min = (float) VSW_Plugin::instance()->settings->get( 'min_score' );
		return $presenter->present( $hits, $min, $limit );
	}

	private function enqueue() {
		wp_enqueue_style( 'vsw-frontend' );
		wp_enqueue_script( 'vsw-frontend' );
	}

	/** @param array|string $atts Shortcode attributes. */
	public function visual_search( $atts ) {
		$atts = shortcode_atts( array( 'label' => __( 'Search by photo', 'visual-search-for-woocommerce' ) ), $atts, 'vsw_visual_search' );
		$this->enqueue();
		return $this->render( 'button', array( 'label' => $atts['label'] ) );
	}

	/** @param string $form Search form HTML. */
	public function append_to_search_form( $form ) {
		return $form . $this->visual_search( array() );
	}

	/** @param array|string $atts Shortcode attributes. */
	public function similar_shortcode( $atts ) {
		$atts = shortcode_atts(
			array(
				'id'    => get_the_ID(),
				'limit' => $this->settings->get( 'similar_count' ),
				'title' => __( 'You may also like', 'visual-search-for-woocommerce' ),
			),
			$atts,
			'vsw_similar_products'
		);
		$products = self::similar_products( $this->api, $this->presenter, $atts['id'], $atts['limit'] );
		if ( ! $products ) {
			return '';
		}
		wp_enqueue_style( 'vsw-frontend' );
		return $this->render(
			'similar-products',
			array(
				'title'    => $atts['title'],
				'products' => $products,
			)
		);
	}

	public function render_on_product_page() {
		echo $this->similar_shortcode( array( 'id' => get_the_ID() ) ); // phpcs:ignore WordPress.Security.EscapeOutput -- template escapes.
	}

	public function print_modal() {
		if ( $this->modal_printed || ! wp_script_is( 'vsw-frontend', 'enqueued' ) ) {
			return;
		}
		$this->modal_printed = true;
		echo $this->render( 'modal', array() ); // phpcs:ignore WordPress.Security.EscapeOutput -- template escapes.
	}

	/**
	 * Render a template from /templates. Themes can override it by copying it
	 * to yourtheme/visual-search-for-woocommerce/<name>.php.
	 *
	 * @param string $name Template name.
	 * @param array  $vars Variables available in the template.
	 */
	private function render( $name, array $vars ) {
		$file = locate_template( 'visual-search-for-woocommerce/' . $name . '.php' );
		if ( ! $file ) {
			$file = VSW_DIR . 'templates/' . $name . '.php';
		}
		ob_start();
		( static function ( $__file, $__vars ) {
			extract( $__vars, EXTR_SKIP ); // phpcs:ignore WordPress.PHP.DontExtract
			include $__file;
		} )( $file, $vars );
		return (string) ob_get_clean();
	}
}
