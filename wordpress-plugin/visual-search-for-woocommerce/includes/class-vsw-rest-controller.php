<?php
/**
 * Public REST endpoints used by the storefront widget (and mobile apps).
 *
 *   POST /wp-json/vsw/v1/detect          multipart "image"      -> upload_key + detected items
 *   POST /wp-json/vsw/v1/search          upload_key, bbox, ...  -> product cards
 *   GET  /wp-json/vsw/v1/similar/{id}                          -> product cards
 *
 * The visual search API itself is never exposed to visitors: WordPress
 * validates input, rate-limits, calls the API server-side and only returns
 * published, visible products.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

class VSW_Rest_Controller {

	const NAMESPACE = 'vsw/v1';

	/** @var VSW_Settings */
	private $settings;
	/** @var VSW_Api_Client */
	private $api;
	/** @var VSW_Upload_Store */
	private $uploads;
	/** @var VSW_Product_Presenter */
	private $presenter;

	public function __construct( VSW_Settings $settings, VSW_Api_Client $api, VSW_Upload_Store $uploads, VSW_Product_Presenter $presenter ) {
		$this->settings  = $settings;
		$this->api       = $api;
		$this->uploads   = $uploads;
		$this->presenter = $presenter;
	}

	public function register() {
		add_action( 'rest_api_init', array( $this, 'routes' ) );
	}

	public function routes() {
		register_rest_route(
			self::NAMESPACE,
			'/detect',
			array(
				'methods'             => WP_REST_Server::CREATABLE,
				'callback'            => array( $this, 'detect' ),
				'permission_callback' => array( $this, 'rate_limit' ),
			)
		);
		register_rest_route(
			self::NAMESPACE,
			'/search',
			array(
				'methods'             => WP_REST_Server::CREATABLE,
				'callback'            => array( $this, 'search' ),
				'permission_callback' => array( $this, 'rate_limit' ),
				'args'                => array(
					'upload_key' => array(
						'type'     => 'string',
						'required' => true,
						'pattern'  => '^[A-Za-z0-9]{32}$',
					),
					'bbox'       => array(
						'type'     => 'array',
						'items'    => array( 'type' => 'number' ),
						'minItems' => 4,
						'maxItems' => 4,
					),
					'domain'     => array(
						'type'    => 'string',
						'enum'    => array( 'fashion', 'general' ),
						'default' => 'fashion',
					),
					'label'      => array(
						'type'              => 'string',
						'sanitize_callback' => 'sanitize_text_field',
					),
					'label_ar'   => array(
						'type'              => 'string',
						'sanitize_callback' => 'sanitize_text_field',
					),
				),
			)
		);
		register_rest_route(
			self::NAMESPACE,
			'/similar/(?P<id>\d+)',
			array(
				'methods'             => WP_REST_Server::READABLE,
				'callback'            => array( $this, 'similar' ),
				'permission_callback' => array( $this, 'rate_limit' ),
				'args'                => array(
					'id' => array(
						'type'    => 'integer',
						'minimum' => 1,
					),
				),
			)
		);
	}

	/**
	 * Fixed-window rate limit per visitor (hashed IP), stored in a transient.
	 * Model inference is expensive, so anonymous endpoints must be throttled.
	 *
	 * @return true|WP_Error
	 */
	public function rate_limit() {
		$ip     = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
		$bucket = 'vsw_rl_' . substr( hash_hmac( 'sha256', $ip, wp_salt( 'nonce' ) ), 0, 20 );
		$count  = (int) get_transient( $bucket );
		$limit  = (int) $this->settings->get( 'rate_limit' );
		if ( $count >= $limit ) {
			return new WP_Error( 'vsw_rate_limited', __( 'Too many searches — please wait a few minutes.', 'visual-search-for-woocommerce' ), array( 'status' => 429 ) );
		}
		set_transient( $bucket, $count + 1, 5 * MINUTE_IN_SECONDS );
		return true;
	}

	public function detect( WP_REST_Request $request ) {
		$files = $request->get_file_params();
		if ( empty( $files['image'] ) ) {
			return new WP_Error( 'vsw_no_image', __( 'No image uploaded.', 'visual-search-for-woocommerce' ), array( 'status' => 400 ) );
		}
		$stored = $this->uploads->store( $files['image'] );
		if ( is_wp_error( $stored ) ) {
			return $stored;
		}
		$data = $this->api->detect( $stored['path'], $stored['mime'] );
		if ( is_wp_error( $data ) ) {
			return $data;
		}

		$items = array();
		foreach ( (array) ( $data['items'] ?? array() ) as $item ) {
			$items[] = array(
				'label'    => sanitize_text_field( $item['label'] ?? '' ),
				'label_ar' => sanitize_text_field( $item['label_ar'] ?? '' ),
				'icon'     => sanitize_text_field( $item['icon'] ?? '' ),
				'domain'   => ( 'general' === ( $item['domain'] ?? '' ) ) ? 'general' : 'fashion',
				'bbox'     => array_map( 'floatval', array_slice( (array) ( $item['bbox'] ?? array() ), 0, 4 ) ),
				'score'    => (float) ( $item['score'] ?? 0 ),
			);
		}

		return rest_ensure_response(
			array(
				'upload_key' => $stored['key'],
				'image_size' => array_map( 'intval', (array) ( $data['image_size'] ?? array( 0, 0 ) ) ),
				'items'      => $items,
			)
		);
	}

	public function search( WP_REST_Request $request ) {
		$upload = $this->uploads->get( $request['upload_key'] );
		if ( is_wp_error( $upload ) ) {
			return $upload;
		}

		$top_k = (int) $this->settings->get( 'top_k' );
		// The whole-image fallback item ("Product") carries no category signal.
		$hints = array_diff( array_filter( array( $request['label'], $request['label_ar'] ) ), array( 'Product', 'منتج' ) );
		// Ask for more than we show: some hits are filtered out below
		// (hidden/draft products, storefront score cut-off).
		$data = $this->api->search(
			$upload['path'],
			$upload['mime'],
			array(
				'top_k'         => max( $top_k * 4, 48 ),
				'bbox'          => $request['bbox'],
				'domain'        => $request['domain'],
				// Category re-ranking: products whose category contains the
				// detected label ("Dress" / "فستان") are moved to the top.
				'category_hint' => implode( ',', $hints ),
			)
		);
		if ( is_wp_error( $data ) ) {
			return $data;
		}

		return rest_ensure_response(
			array(
				'products' => $this->presenter->present( (array) ( $data['results'] ?? array() ), (float) $this->settings->get( 'min_score' ), $top_k ),
			)
		);
	}

	public function similar( WP_REST_Request $request ) {
		$limit = (int) $this->settings->get( 'similar_count' );
		return rest_ensure_response( array( 'products' => VSW_Shortcodes::similar_products( $this->api, $this->presenter, (int) $request['id'], $limit ) ) );
	}
}
