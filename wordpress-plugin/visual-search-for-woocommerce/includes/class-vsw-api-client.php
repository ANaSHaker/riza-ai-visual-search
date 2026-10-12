<?php
/**
 * Thin HTTP client for the visual search API.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

class VSW_Api_Client {

	/** @var VSW_Settings */
	private $settings;

	public function __construct( VSW_Settings $settings ) {
		$this->settings = $settings;
	}

	private function url( $path ) {
		return untrailingslashit( (string) $this->settings->get( 'api_url' ) ) . $path;
	}

	private function headers( array $extra = array() ) {
		$headers = array( 'Accept' => 'application/json' );
		$key     = (string) $this->settings->get( 'api_key' );
		if ( '' !== $key ) {
			$headers['X-API-Key'] = $key;
		}
		return array_merge( $headers, $extra );
	}

	/**
	 * Decode a response; any transport error or non-2xx becomes a WP_Error
	 * with a generic message (details go to the PHP error log, not the visitor).
	 *
	 * @param array|WP_Error $resp Response.
	 * @return array|WP_Error
	 */
	private function decode( $resp ) {
		if ( is_wp_error( $resp ) ) {
			error_log( 'Visual Search API transport error: ' . $resp->get_error_message() ); // phpcs:ignore WordPress.PHP.DevelopmentFunctions
			return new WP_Error( 'vsw_api_unreachable', __( 'Visual search is temporarily unavailable.', 'visual-search-for-woocommerce' ), array( 'status' => 502 ) );
		}
		$code = (int) wp_remote_retrieve_response_code( $resp );
		$body = json_decode( wp_remote_retrieve_body( $resp ), true );
		if ( $code < 200 || $code >= 300 || ! is_array( $body ) ) {
			error_log( 'Visual Search API HTTP ' . $code ); // phpcs:ignore WordPress.PHP.DevelopmentFunctions
			$status = ( 404 === $code ) ? 404 : 502;
			return new WP_Error( 'vsw_api_error', __( 'Visual search request failed.', 'visual-search-for-woocommerce' ), array( 'status' => $status ) );
		}
		return $body;
	}

	/**
	 * multipart/form-data POST with one image file plus scalar fields.
	 *
	 * @param string $path   Endpoint path.
	 * @param string $file   Absolute path of the stored upload.
	 * @param string $mime   Validated MIME type.
	 * @param array  $fields Extra form fields.
	 * @param int    $timeout Seconds.
	 */
	private function post_image( $path, $file, $mime, array $fields = array(), $timeout = 40 ) {
		$boundary = 'vsw' . wp_generate_password( 24, false );
		$eol      = "\r\n";
		$body     = '--' . $boundary . $eol
			. 'Content-Disposition: form-data; name="image"; filename="upload"' . $eol
			. 'Content-Type: ' . $mime . $eol . $eol
			. file_get_contents( $file ) . $eol; // phpcs:ignore WordPress.WP.AlternativeFunctions
		foreach ( $fields as $name => $value ) {
			$body .= '--' . $boundary . $eol
				. 'Content-Disposition: form-data; name="' . preg_replace( '/[^a-z_]/', '', $name ) . '"' . $eol . $eol
				. $value . $eol;
		}
		$body .= '--' . $boundary . '--' . $eol;

		return $this->decode(
			wp_remote_post(
				$this->url( $path ),
				array(
					'timeout' => $timeout,
					'headers' => $this->headers( array( 'Content-Type' => 'multipart/form-data; boundary=' . $boundary ) ),
					'body'    => $body,
				)
			)
		);
	}

	private function post_json( $path, array $payload, $timeout = 30, $blocking = true ) {
		$resp = wp_remote_post(
			$this->url( $path ),
			array(
				'timeout'  => $timeout,
				'blocking' => $blocking,
				'headers'  => $this->headers( array( 'Content-Type' => 'application/json' ) ),
				'body'     => wp_json_encode( $payload ),
			)
		);
		return $blocking ? $this->decode( $resp ) : true;
	}

	// ---------------------------------------------------------------- reads

	public function health() {
		return $this->decode( wp_remote_get( $this->url( '/health' ), array( 'timeout' => 5 ) ) );
	}

	public function detect( $file, $mime ) {
		// The detector may be loading on the very first call; allow extra time.
		return $this->post_image( '/v1/detect', $file, $mime, array(), 90 );
	}

	/**
	 * @param string $file   Stored upload path.
	 * @param string $mime   MIME type.
	 * @param array  $args   bbox (array|null), top_k, domain, category_hint (string).
	 */
	public function search( $file, $mime, array $args ) {
		$fields = array(
			'top_k'  => (string) (int) $args['top_k'],
			'domain' => 'general' === ( $args['domain'] ?? '' ) ? 'general' : 'fashion',
		);
		if ( ! empty( $args['bbox'] ) ) {
			$fields['bbox'] = wp_json_encode( array_map( 'floatval', $args['bbox'] ) );
		}
		if ( ! empty( $args['category_hint'] ) ) {
			$fields['category_hint'] = $args['category_hint'];
		}
		return $this->post_image( '/v1/search', $file, $mime, $fields );
	}

	public function similar( $product_id, $top_k ) {
		$url = add_query_arg( array( 'top_k' => (int) $top_k ), $this->url( '/v1/products/' . absint( $product_id ) . '/similar' ) );
		return $this->decode( wp_remote_get( $url, array( 'timeout' => 10, 'headers' => $this->headers() ) ) );
	}

	// --------------------------------------------------------------- writes

	/**
	 * @param array $items list of { product_id, image_url, categories[] }.
	 * @param bool  $blocking Wait for the response (admin batch) or fire-and-forget (on save).
	 */
	public function index_batch( array $items, $blocking = true ) {
		return $this->post_json( '/v1/index/batch', array( 'items' => array_values( $items ) ), 300, $blocking );
	}

	public function delete_product( $product_id ) {
		return wp_remote_request(
			$this->url( '/v1/index/products/' . absint( $product_id ) ),
			array(
				'method'   => 'DELETE',
				'blocking' => false,
				'headers'  => $this->headers(),
			)
		);
	}

	public function rebuild() {
		return $this->post_json( '/v1/index/rebuild', array(), 120 );
	}
}
